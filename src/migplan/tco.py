"""Five-year TCO: stay on premises vs migrate on the wave plan, month by month, with NPV and break-even.

Every number used is in TcoAssumptions and is returned by the API next to the result. Prices are planning
figures in the range of public list prices, not quotes. The catalog uses generic instance names on purpose.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date

from .classify import Classification
from .models import Estate, Server

HOURS_PER_MONTH = 730


@dataclass
class TcoAssumptions:
    months: int = 60
    discount_rate: float = 0.08  # annual, applied monthly
    # on premises
    refresh_years: int = 5
    refresh_physical_usd: float = 18_000  # per physical server
    refresh_virtual_per_vcpu_usd: float = 450  # host capacity share per vCPU
    refresh_virtual_per_gb_usd: float = 25  # host memory, storage array, and network share per GB
    san_usd_per_gb_month: float = 0.10  # includes replication and backup
    watts_physical: float = 450
    watts_per_vcpu: float = 12
    pue: float = 1.6
    usd_per_kwh: float = 0.13
    facility_usd_per_server_month: float = 55  # rack space, network, colo contract share
    vmware_usd_per_vcpu_year: float = 85
    windows_usd_per_server_year: float = 900
    rhel_usd_per_server_year: float = 800
    unix_support_usd_per_server_year: float = 3_000
    oracle_support_usd_per_license_year: float = 10_450  # 22% of a 47,500 processor license
    oracle_core_factor_onprem: float = 0.5  # x86 core factor on premises
    sql_support_usd_per_core_year: float = 1_890  # Software Assurance on Enterprise
    onprem_servers_per_fte: int = 60
    fte_usd_year: float = 150_000
    mainframe_usd_year: float = 4_200_000  # retained in both scenarios
    # cloud
    target_cpu_util: float = 0.65
    target_mem_util: float = 0.80
    min_vcpu: int = 2
    usd_per_vcpu_hour: dict[str, float] = field(
        default_factory=lambda: {"general": 0.048, "memory": 0.063, "compute": 0.0425}
    )
    gb_per_vcpu: dict[str, int] = field(default_factory=lambda: {"general": 4, "memory": 8, "compute": 2})
    sizes_vcpu: tuple[int, ...] = (2, 4, 8, 16, 32, 48, 64, 96)
    commit_discount_prod: float = 0.30  # one year compute commitment on steady prod load
    nonprod_hours_per_week: float = 50  # scheduled off nights and weekends
    windows_usd_per_vcpu_hour: float = 0.046  # license included
    rhel_usd_per_vcpu_hour: float = 0.013
    oracle_vcpus_per_license: int = 2  # authorized cloud policy: 2 vCPUs = 1 processor license, no core factor
    managed_db_premium: float = 1.5  # managed database instance vs the same VM
    refactor_compute_factor: float = 0.6  # containers and autoscaling
    block_usd_per_gb_month: float = 0.08
    snapshot_share: float = 0.2
    snapshot_usd_per_gb_month: float = 0.05
    wan_egress_usd_per_gb: float = 0.02  # cloud to on premises over the private link
    private_link_usd_month: float = 3_300  # two redundant 10 Gbps ports
    landing_zone_usd_month: float = 25_000  # security tooling, logging, backup, shared networking
    cloud_instances_per_fte: int = 150
    saas_usd_per_user_month: float = 35
    saas_min_usd_year: float = 12_000
    # one time
    migrate_usd: dict[str, float] = field(
        default_factory=lambda: {
            "rehost": 8_000,
            "replatform": 25_000,
            "refactor": 150_000,
            "repurchase": 40_000,
            "retire": 8_000,
        }
    )
    migrate_per_server_usd: dict[str, float] = field(
        default_factory=lambda: {"rehost": 1_500, "replatform": 2_500, "refactor": 0, "repurchase": 0, "retire": 500}
    )
    dual_run_months: int = 2  # on premises keeps running after cutover until decommission
    retire_month: int = 6
    training_usd_per_team: float = 25_000  # teams with cloud skill 0 or 1
    plan_start: date = date(2027, 1, 1)

    def describe(self) -> dict:
        return asdict(self) | {"plan_start": str(self.plan_start)}


def rightsize(server: Server, a: TcoAssumptions) -> dict:
    """Smallest catalog instance that holds p95 CPU and memory at the target utilization."""
    need_vcpu = max(a.min_vcpu, math.ceil(server.cores * server.cpu_p95 / a.target_cpu_util))
    need_gb = server.ram_gb * server.mem_p95 / a.target_mem_util
    best = None
    for family, ratio in a.gb_per_vcpu.items():
        for size in a.sizes_vcpu:
            if size >= need_vcpu and size * ratio >= need_gb:
                cost = size * a.usd_per_vcpu_hour[family]
                if best is None or cost < best["usd_hour"]:
                    best = {
                        "family": family,
                        "vcpu": size,
                        "ram_gb": size * ratio,
                        "usd_hour": cost,
                        "name": f"{family}-{size}x{size * ratio}",
                    }
                break
    if best is None:  # larger than the catalog: largest memory size
        size = a.sizes_vcpu[-1]
        best = {
            "family": "memory",
            "vcpu": size,
            "ram_gb": size * 8,
            "usd_hour": size * a.usd_per_vcpu_hour["memory"],
            "name": f"memory-{size}x{size * 8}",
        }
    return best


def onprem_server_year(s: Server, db_engine: str, a: TcoAssumptions) -> dict:
    """Annual run cost of one server on premises, by component (excludes refresh capex)."""
    kw = (a.watts_physical if s.physical else s.cores * a.watts_per_vcpu) / 1000
    out = {
        "storage": s.storage_gb * a.san_usd_per_gb_month * 12,
        "power": kw * a.pue * 8760 * a.usd_per_kwh,
        "facility": a.facility_usd_per_server_month * 12,
        "virtualization": 0.0 if s.physical else s.cores * a.vmware_usd_per_vcpu_year,
        "os": (
            a.windows_usd_per_server_year
            if s.os.startswith("Windows")
            else a.unix_support_usd_per_server_year
            if s.os.startswith(("AIX", "Solaris"))
            else a.rhel_usd_per_server_year
        ),
        "db_license": 0.0,
        "staff": a.fte_usd_year / a.onprem_servers_per_fte,
    }
    if s.role == "db" and db_engine.startswith("Oracle"):
        out["db_license"] = s.cores * a.oracle_core_factor_onprem * a.oracle_support_usd_per_license_year
    elif s.role == "db" and db_engine.startswith("SQL Server"):
        out["db_license"] = s.cores * a.sql_support_usd_per_core_year
    return out


def refresh_cost(s: Server, a: TcoAssumptions) -> float:
    if s.physical:
        return a.refresh_physical_usd
    return s.cores * a.refresh_virtual_per_vcpu_usd + s.ram_gb * a.refresh_virtual_per_gb_usd


def refresh_months(s: Server, a: TcoAssumptions) -> list[int]:
    first = max(0, (a.refresh_years - s.hw_age_years) * 12)
    return list(range(first, a.months, a.refresh_years * 12))


def cloud_server_year(s: Server, db_engine: str, strategy: str, a: TcoAssumptions) -> dict:
    inst = rightsize(s, a)
    hours = HOURS_PER_MONTH * 12 if s.env == "prod" else a.nonprod_hours_per_week * 52
    discount = a.commit_discount_prod if s.env == "prod" else 0.0
    compute = inst["usd_hour"] * hours * (1 - discount)
    db_license = os_license = 0.0
    if strategy == "refactor" and s.role != "db":
        compute *= a.refactor_compute_factor
    elif s.os.startswith("Windows"):
        os_license = a.windows_usd_per_vcpu_hour * inst["vcpu"] * hours
    else:
        os_license = a.rhel_usd_per_vcpu_hour * inst["vcpu"] * hours
    if s.role == "db":
        if strategy in ("replatform", "refactor"):
            compute *= a.managed_db_premium
            os_license = 0.0
        if db_engine.startswith("Oracle") and strategy == "rehost":
            db_license = math.ceil(inst["vcpu"] / a.oracle_vcpus_per_license) * a.oracle_support_usd_per_license_year
        elif db_engine.startswith("SQL Server") and strategy == "rehost":
            db_license = max(4, inst["vcpu"]) * a.sql_support_usd_per_core_year
        elif db_engine.startswith(("Oracle", "SQL Server")):
            # replatform: Oracle to managed PostgreSQL, SQL Server to a managed instance with license included
            db_license = 0.0 if db_engine.startswith("Oracle") else inst["vcpu"] * 0.30 * hours
    storage = s.storage_gb * (a.block_usd_per_gb_month + a.snapshot_share * a.snapshot_usd_per_gb_month) * 12
    return {
        "instance": inst["name"],
        "compute": compute,
        "os": os_license,
        "db_license": db_license,
        "storage": storage,
        "staff": a.fte_usd_year / a.cloud_instances_per_fte,
    }


def npv(cashflows: list[float], annual_rate: float) -> float:
    """Net present value of monthly cash flows; month 0 is discounted one month."""
    r = (1 + annual_rate) ** (1 / 12) - 1
    return sum(cf / (1 + r) ** (m + 1) for m, cf in enumerate(cashflows))


def break_even_month(savings: list[float]) -> int | None:
    """First month (1-based) after which cumulative savings are non-negative and stay that way."""
    cum, last_negative = 0.0, None
    seen_negative = False
    for m, s in enumerate(savings):
        cum += s
        if cum < 0:
            last_negative, seen_negative = m, True
    if not seen_negative:
        return 1 if savings else None
    if cum < 0 or last_negative is None:
        return None
    return last_negative + 2


def compute_tco(
    estate: Estate,
    classes: dict[str, Classification],
    cutover: dict[str, int],
    a: TcoAssumptions | None = None,
    hub: tuple[str, int] | None = None,
    gb_edges: dict[tuple[str, str], float] | None = None,
) -> dict:
    """cutover maps app id to its wave (1-based month of cutover). hub is (app id, wave) for the shared database.
    gb_edges maps (consumer, provider) to GB per day, from discovery; it prices the traffic that keeps crossing
    the private link after the program."""
    a = a or TcoAssumptions()
    n = a.months
    base = [0.0] * n
    scen = [0.0] * n
    one_time = [0.0] * n
    by_cat = {"onprem_run": 0.0, "refresh_capex_avoided": 0.0, "cloud_run_year": 0.0, "one_time": 0.0}
    cut = dict(cutover)
    if hub:
        cut[hub[0]] = hub[1]
    instances = 0
    per_app = {}
    egress_gb_month = 0.0
    for app_id, app in estate.apps.items():
        strat = classes[app_id].strategy
        servers = estate.servers_of(app_id)
        if app.kind == "mainframe":
            for m in range(n):
                base[m] += a.mainframe_usd_year / 12
                scen[m] += a.mainframe_usd_year / 12
            continue
        on_year = sum(sum(onprem_server_year(s, app.db_engine, a).values()) for s in servers)
        refresh = [(m, refresh_cost(s, a)) for s in servers for m in refresh_months(s, a)]
        for m in range(n):
            base[m] += on_year / 12
        for m, c in refresh:
            base[m] += c
        if strat == "retain" or (strat != "retire" and app_id not in cut):
            for m in range(n):
                scen[m] += on_year / 12
            for m, c in refresh:
                scen[m] += c
            per_app[app_id] = {"onprem_year": on_year, "cloud_year": None}
            continue
        if strat == "retire":
            end = min(n, a.retire_month)
            for m in range(end):
                scen[m] += on_year / 12
            for m, c in refresh:
                if m < end:
                    scen[m] += c
            cost = a.migrate_usd["retire"] + a.migrate_per_server_usd["retire"] * len(servers)
            one_time[min(n - 1, max(0, end - 3))] += cost
            per_app[app_id] = {"onprem_year": on_year, "cloud_year": 0.0, "one_time": cost}
            continue
        wave = cut[app_id]
        live = wave  # cloud costs start the month after the wave month (0-based index = wave)
        off = min(n, wave + a.dual_run_months)
        if strat == "repurchase":
            cloud_year = max(a.saas_min_usd_year, a.saas_usd_per_user_month * 12 * app.monthly_users)
        else:
            cloud_year = sum(
                sum(v for k, v in cloud_server_year(s, app.db_engine, strat, a).items() if k != "instance")
                for s in servers
            )
            instances += len(servers)
        for m in range(n):
            if m < off:
                scen[m] += on_year / 12
            if m >= live:
                scen[m] += cloud_year / 12
        for m, c in refresh:
            if m < off:
                scen[m] += c
            else:
                by_cat["refresh_capex_avoided"] += c
        cost = a.migrate_usd[strat] + a.migrate_per_server_usd[strat] * len(servers)
        one_time[max(0, wave - 2)] += cost * 0.5  # spend splits across the prep month and the wave month
        one_time[max(0, wave - 1)] += cost * 0.5
        per_app[app_id] = {"onprem_year": on_year, "cloud_year": cloud_year, "one_time": cost}
        by_cat["cloud_run_year"] += cloud_year
    # traffic that keeps crossing the private link after the program: migrated apps calling retained ones
    retained = {x for x, c in classes.items() if c.strategy == "retain"}
    for (src, dst), gb_day in (gb_edges or {}).items():
        if (
            (src in retained) != (dst in retained)
            and classes[src].strategy != "retire"
            and classes[dst].strategy != "retire"
        ):
            egress_gb_month += gb_day * 30
    first_live = min(cut.values()) if cut else 0
    for m in range(n):
        if m >= max(0, first_live - 1):
            scen[m] += a.landing_zone_usd_month + a.private_link_usd_month
        if m >= first_live:
            scen[m] += egress_gb_month * a.wan_egress_usd_per_gb
    low_skill = sum(1 for t in estate.teams.values() if t.cloud_skill <= 1)
    one_time[0] += low_skill * a.training_usd_per_team
    scen = [s + o for s, o in zip(scen, one_time, strict=True)]
    savings = [b - s for b, s in zip(base, scen, strict=True)]
    cum, cum_list = 0.0, []
    for s in savings:
        cum += s
        cum_list.append(cum)
    be = break_even_month(savings)
    by_cat["onprem_run"] = sum(p["onprem_year"] for p in per_app.values())
    by_cat["one_time"] = sum(one_time)
    yearly = [
        {
            "year": y + 1,
            "onprem": round(sum(base[y * 12 : (y + 1) * 12])),
            "migrate": round(sum(scen[y * 12 : (y + 1) * 12])),
            "savings": round(sum(savings[y * 12 : (y + 1) * 12])),
        }
        for y in range(n // 12)
    ]
    be_date = None
    if be:
        m0 = a.plan_start.month - 1 + be - 1
        be_date = str(date(a.plan_start.year + m0 // 12, m0 % 12 + 1, 1))
    return {
        "months": n,
        "onprem_monthly": [round(x) for x in base],
        "migrate_monthly": [round(x) for x in scen],
        "one_time_monthly": [round(x) for x in one_time],
        "cumulative_savings": [round(x) for x in cum_list],
        "onprem_total": round(sum(base)),
        "migrate_total": round(sum(scen)),
        "one_time_total": round(sum(one_time)),
        "npv": round(npv(savings, a.discount_rate)),
        "break_even_month": be,
        "break_even_date": be_date,
        "steady_state_annual_savings": round((base[-1] - scen[-1]) * 12) if n else 0,
        "yearly": yearly,
        "refresh_capex_avoided": round(by_cat["refresh_capex_avoided"]),
        "cloud_instances": instances,
        "egress_gb_month_after_program": round(egress_gb_month),
        "assumptions": a.describe(),
    }
