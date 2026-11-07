from collections import defaultdict

import pytest

from migplan.classify import Classification
from migplan.discovery import discover
from migplan.models import Flow
from migplan.waves import (
    WaveConfig,
    build_plan,
    build_problem,
    compare,
    evaluate_plan,
    plan_alphabetical,
    plan_optimized,
    violations,
)

from .conftest import make_app, make_server, tiny_estate

GB = 1_000_000_000


@pytest.fixture(scope="module")
def cmp_(planner):
    return compare(planner.problem)


@pytest.mark.parametrize("method", ["optimized", "alphabetical", "business_unit"])
def test_every_planner_respects_all_hard_constraints(planner, cmp_, method):
    plan = cmp_["plans"][method]
    assert violations(planner.problem, plan.where) == []
    assert plan.metrics["unscheduled"] == 0


def test_freeze_windows_respected_by_calendar_month(planner):
    p = planner.problem
    for a, w in planner.plan.where.items():
        assert p.wave_month(w) not in planner.estate.apps[a].freeze_months, a


def test_team_unavailability_and_capacity(planner):
    p = planner.problem
    per = defaultdict(int)
    for a, w in planner.plan.where.items():
        team = planner.estate.teams[p.team[a]]
        assert w not in team.unavailable_waves
        per[(w, team.name)] += 1
    for (_w, t), n in per.items():
        assert n <= planner.estate.teams[t].capacity_per_wave


def test_pilot_wave_is_low_risk_and_critical_apps_wait(planner):
    p = planner.problem
    pilots = [a for a, w in planner.plan.where.items() if w == 1]
    assert 3 <= len(pilots)
    for a in pilots:
        app = planner.estate.apps[a]
        assert app.criticality >= 3 and not app.compliance and not app.latency_sensitive
    for a, w in planner.plan.where.items():
        if planner.estate.apps[a].criticality == 1:
            assert w >= p.cfg.critical_not_before


def test_shared_database_handled_explicitly(planner):
    p = planner.problem
    assert p.hub == "APP-249" and p.hub not in p.movable and len(p.hub_weights) >= 20
    hw = planner.plan.hub_wave
    assert hw and p.wave_month(hw) not in planner.estate.apps[p.hub].freeze_months


def test_optimized_beats_both_naive_plans_on_cut_weight(cmp_):
    rows = {r["method"]: r for r in cmp_["rows"]}
    opt = rows["optimized"]["total_cut_weight"]
    assert opt < rows["alphabetical"]["total_cut_weight"] * 0.5
    assert opt < rows["business_unit"]["total_cut_weight"] * 0.5
    assert rows["optimized"]["split_edges"] < rows["business_unit"]["split_edges"]
    assert rows["optimized"]["total_wan_gb"] < rows["business_unit"]["total_wan_gb"]


def test_plan_is_deterministic(planner):
    a = build_plan(planner.problem).where
    b = build_plan(planner.problem).where
    assert a == b


def _toy(max_effort=2.0, freeze_c=()):
    """Two chatty pairs (A-B, C-D) and one light link B-C; waves fit two apps each."""
    apps = [
        make_app(
            x,
            owner_team="team-a" if x in "AB" else "team-b",
            criticality=3,
            freeze_months=list(freeze_c) if x == "C" else [],
        )
        for x in "ABCD"
    ]
    servers = [make_server(f"S{x}", x, f"10.0.0.{i}") for i, x in enumerate("ABCD", 1)]
    flows = [
        Flow("10.0.0.1", "10.0.0.2", 443, "tcp", 100_000, 50 * GB),
        Flow("10.0.0.3", "10.0.0.4", 443, "tcp", 100_000, 50 * GB),
        Flow("10.0.0.2", "10.0.0.3", 443, "tcp", 1000, 1 * GB),
    ]
    e = tiny_estate(apps, servers, flows)
    d = discover(e)
    classes = {x: Classification(x, "rehost", "rehost", {}, [], 1.0) for x in "ABCD"}
    cfg = WaveConfig(
        n_waves=3,
        max_effort=max_effort,
        max_servers=10,
        pilot_max_effort=max_effort,
        critical_not_before=1,
        cluster_fill=1.0,
    )
    return build_problem(e, d, classes, cfg)


def test_toy_partition_keeps_chatty_pairs_together():
    p = _toy()
    where = plan_optimized(p)
    assert where["A"] == where["B"] and where["C"] == where["D"] and where["A"] != where["C"]
    m = evaluate_plan(p, where, None)
    assert m["split_edges"] == 1 and m["cut_weight"] == pytest.approx(p.weights[("B", "C")])


def test_toy_alphabetical_is_worse_when_names_interleave():
    p = _toy()
    for a, name in zip("ABCD", ["Alpha", "Delta", "Bravo", "Echo"], strict=True):
        p.estate.apps[a].name = name
    naive = evaluate_plan(p, plan_alphabetical(p), None)
    opt = evaluate_plan(p, plan_optimized(p), None)
    assert naive["cut_weight"] > opt["cut_weight"]


def test_toy_capacity_is_never_exceeded_even_if_apps_stay_unscheduled():
    p = _toy(max_effort=1.0)  # one app per wave, three waves, four apps
    where = plan_optimized(p)
    assert violations(p, where) == []
    assert len(where) == 3
    assert evaluate_plan(p, where, None)["unscheduled"] == 1


def test_toy_freeze_splits_a_pair_rather_than_breaking_the_freeze():
    p = _toy(freeze_c=(1, 2))  # C can only move in wave 3 (March)
    where = plan_optimized(p)
    assert where["C"] == 3 and violations(p, where) == []
