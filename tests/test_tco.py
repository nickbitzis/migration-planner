import math

import pytest

from migplan.classify import Classification
from migplan.tco import (
    TcoAssumptions,
    break_even_month,
    cloud_server_year,
    compute_tco,
    npv,
    onprem_server_year,
    refresh_months,
    rightsize,
)

from .conftest import make_app, make_server, tiny_estate


def test_npv_zero_rate_is_plain_sum():
    assert npv([100.0] * 12, 0.0) == pytest.approx(1200.0)


def test_npv_discounts_monthly_from_the_annual_rate():
    r = 1.08 ** (1 / 12) - 1
    assert npv([1000.0], 0.08) == pytest.approx(1000 / (1 + r))
    assert npv([0.0] * 11 + [1000.0], 0.08) == pytest.approx(1000 / 1.08)


@pytest.mark.parametrize(
    "savings, month",
    [
        ([-10, 5, 5], 3),  # cumulative -10, -5, 0
        ([-10, 4, 4, 4], 4),
        ([5, 5], 1),  # never negative
        ([-10, 20, -15, 10], 4),  # dips back below zero in month 3, recovers in month 4
        ([-10, 1, 1], None),  # never recovers
    ],
)
def test_break_even_month(savings, month):
    assert break_even_month(savings) == month


def test_rightsize_picks_the_cheapest_instance_that_fits():
    a = TcoAssumptions()
    s = make_server("S", "A", "10.0.0.1", cores=16, ram_gb=64, cpu_p95=0.2, mem_p95=0.5)
    # need ceil(16 * 0.2 / 0.65) = 5 vCPU and 64 * 0.5 / 0.8 = 40 GB
    inst = rightsize(s, a)
    assert inst["name"] == "memory-8x64"
    assert inst["usd_hour"] == pytest.approx(8 * 0.063)


def test_rightsize_respects_minimum_and_compute_family():
    a = TcoAssumptions()
    s = make_server("S", "A", "10.0.0.1", cores=4, ram_gb=4, cpu_p95=0.05, mem_p95=0.5)
    assert rightsize(s, a)["name"] == "compute-2x4"


def test_onprem_oracle_license_uses_core_factor():
    a = TcoAssumptions()
    s = make_server("D", "A", "10.0.0.1", role="db", cores=16)
    y = onprem_server_year(s, "Oracle 19c", a)
    assert y["db_license"] == pytest.approx(16 * 0.5 * 10_450)


def test_cloud_oracle_byol_counts_two_vcpus_per_license_and_replatform_drops_it():
    a = TcoAssumptions()
    s = make_server("D", "A", "10.0.0.1", role="db", cores=16, ram_gb=64, cpu_p95=0.6, mem_p95=0.5)
    inst = rightsize(s, a)
    rehost = cloud_server_year(s, "Oracle 19c", "rehost", a)
    assert rehost["db_license"] == pytest.approx(math.ceil(inst["vcpu"] / 2) * 10_450)
    replat = cloud_server_year(s, "Oracle 19c", "replatform", a)
    assert replat["db_license"] == 0 and replat["compute"] == pytest.approx(rehost["compute"] * 1.5)


def test_nonprod_runs_on_a_schedule_without_commitment():
    a = TcoAssumptions()
    s = make_server("N", "A", "10.0.0.1", env="nonprod", cores=4, ram_gb=8, cpu_p95=0.3, mem_p95=0.5)
    inst = rightsize(s, a)
    assert cloud_server_year(s, "none", "rehost", a)["compute"] == pytest.approx(inst["usd_hour"] * 50 * 52)


def test_refresh_months_follow_hardware_age():
    a = TcoAssumptions()
    assert refresh_months(make_server("S", None, "1", hw_age_years=7), a) == [0]
    assert refresh_months(make_server("S", None, "1", hw_age_years=2), a) == [36]


def _one_app_estate(strategy="rehost"):
    app = make_app("A", owner_team="team-a")
    s = make_server("S1", "A", "10.0.0.1", cores=8, ram_gb=32, cpu_p95=0.3, mem_p95=0.5, storage_gb=100, hw_age_years=4)
    e = tiny_estate([app], [s], [])
    return e, {"A": Classification("A", strategy, strategy, {}, [], 1.0)}, s


def test_hand_built_tco_matches_component_math():
    a = TcoAssumptions(
        months=24, landing_zone_usd_month=0, private_link_usd_month=0, training_usd_per_team=0, discount_rate=0.0
    )
    e, classes, s = _one_app_estate()
    out = compute_tco(e, classes, {"A": 3}, a)
    on_year = sum(onprem_server_year(s, "none", a).values())
    cloud_year = sum(v for k, v in cloud_server_year(s, "none", "rehost", a).items() if k != "instance")
    refresh = s.cores * a.refresh_virtual_per_vcpu_usd + s.ram_gb * a.refresh_virtual_per_gb_usd  # due month 12
    assert out["onprem_total"] == round(24 * on_year / 12 + refresh)
    one_time = a.migrate_usd["rehost"] + a.migrate_per_server_usd["rehost"]
    assert out["one_time_total"] == one_time
    # on premises until month 5 (wave 3 + 2 dual run months), cloud from month 3, refresh at month 12 avoided
    expected = 5 * on_year / 12 + 21 * cloud_year / 12 + one_time
    assert out["migrate_total"] == round(expected)
    assert out["refresh_capex_avoided"] == round(refresh)
    assert out["npv"] == round(out["onprem_total"] - expected)  # zero discount rate


def test_identical_costs_and_no_one_time_give_zero_npv():
    a = TcoAssumptions(months=12, landing_zone_usd_month=0, private_link_usd_month=0, training_usd_per_team=0)
    e, classes, _ = _one_app_estate("retain")
    out = compute_tco(e, classes, {}, a)
    assert out["npv"] == 0 and out["onprem_total"] == out["migrate_total"]


def test_sample_tco_has_break_even_and_states_assumptions(planner):
    t = planner.tco
    assert t["break_even_month"] and 12 < t["break_even_month"] <= 60
    assert t["npv"] > 0 and t["one_time_total"] > 0 and t["refresh_capex_avoided"] > 0
    assert {"discount_rate", "oracle_vcpus_per_license", "commit_discount_prod", "fte_usd_year"} <= set(
        t["assumptions"]
    )
    assert len(t["onprem_monthly"]) == 60
