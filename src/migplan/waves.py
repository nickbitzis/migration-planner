"""Wave planning: group movable apps into monthly waves so chatty dependencies move together.

The objective is cross-wave dependency traffic: the weight of every edge whose two ends sit in different waves.
While one end is in the cloud and the other is still on premises, that traffic crosses the WAN.

Hard constraints, enforced the same way for every planner so the comparison is fair:
- wave capacity in effort points (rehost 1, replatform 2, refactor 4, repurchase 1.5) and in servers
- each team can only migrate so many apps per wave, and some teams are unavailable in some waves
- no app moves in a calendar month inside its change freeze
- wave 1 is a pilot: only low risk apps (criticality 3 or 4, no compliance scope, not latency sensitive, rehost
  or replatform), and mission critical apps wait until the landing zone has run a few waves
- the shared database is not partitioned with everything else; it gets its own cutover wave, placed at the
  traffic-weighted median of its consumers, outside its freeze, with replication running until then
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .classify import Classification
from .discovery import Discovery
from .models import Estate

MOVABLE = ("rehost", "replatform", "refactor", "repurchase")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class WaveConfig:
    n_waves: int = 14
    max_effort: float = 34.0
    max_servers: int = 110
    pilot_max_effort: float = 10.0
    critical_not_before: int = 4  # criticality 1 apps wait for this wave
    effort: dict[str, float] = field(
        default_factory=lambda: {"rehost": 1.0, "replatform": 2.0, "refactor": 4.0, "repurchase": 1.5}
    )
    wave_days: int = 30
    refine_passes: int = 6
    cluster_fill: float = 0.6  # a merged group may use at most this share of a wave, so groups can share waves
    pilot_single_max_weight: float = 1.0  # apps pulled into the pilot on their own must be this loosely coupled


@dataclass
class Problem:
    """Everything a planner needs, precomputed once."""

    estate: Estate
    cfg: WaveConfig
    movable: list[str]
    strategy: dict[str, str]
    effort: dict[str, float]
    nservers: dict[str, int]
    team: dict[str, str]
    allowed: dict[str, set[int]]
    pilot_ok: dict[str, bool]
    weights: dict[tuple[str, str], float]  # undirected, movable apps only
    adj: dict[str, dict[str, float]]
    gb_per_day: dict[tuple[str, str], float]  # undirected, all apps
    hub: str | None
    hub_weights: dict[str, float]  # consumer -> weight to the hub

    def wave_month(self, w: int) -> int:
        return (self.estate.plan_start.month - 1 + w - 1) % 12 + 1

    def wave_start(self, w: int) -> date:
        m0 = self.estate.plan_start.month - 1 + w - 1
        return date(self.estate.plan_start.year + m0 // 12, m0 % 12 + 1, 1)

    def team_cap(self, team: str) -> int:
        t = self.estate.teams.get(team)
        return t.capacity_per_wave if t else 2

    def wave_effort_cap(self, w: int) -> float:
        return self.cfg.pilot_max_effort if w == 1 else self.cfg.max_effort


def build_problem(
    estate: Estate, disc: Discovery, classes: dict[str, Classification], cfg: WaveConfig | None = None
) -> Problem:
    cfg = cfg or WaveConfig()
    hub = next(
        (a.id for a in estate.apps.values() if a.kind == "shared_database" and classes[a.id].strategy in MOVABLE), None
    )
    movable = sorted(a for a, c in classes.items() if c.strategy in MOVABLE and a != hub)
    mset = set(movable)
    strategy = {a: classes[a].strategy for a in movable}
    effort = {a: cfg.effort[strategy[a]] for a in movable}
    nservers = {a: len(estate.apps[a].server_ids) for a in movable}
    team = {a: estate.apps[a].owner_team for a in movable}
    pilot_ok = {}
    allowed = {}
    for a in movable:
        app = estate.apps[a]
        pilot_ok[a] = (
            app.criticality >= 3
            and not app.compliance
            and not app.latency_sensitive
            and strategy[a] in ("rehost", "replatform")
        )
        t = estate.teams.get(app.owner_team)
        unavailable = set(t.unavailable_waves) if t else set()
        ok = set()
        for w in range(1, cfg.n_waves + 1):
            month = (estate.plan_start.month - 1 + w - 1) % 12 + 1
            if month in app.freeze_months or w in unavailable:
                continue
            if w == 1 and not pilot_ok[a]:
                continue
            if app.criticality == 1 and w < cfg.critical_not_before:
                continue
            ok.add(w)
        allowed[a] = ok
    und = disc.undirected()
    weights = {k: v for k, v in und.items() if k[0] in mset and k[1] in mset}
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), v in weights.items():
        adj[a][b] = v
        adj[b][a] = v
    gb: dict[tuple[str, str], float] = defaultdict(float)
    for (a, b), e in disc.edges.items():
        gb[(a, b) if a < b else (b, a)] += e.gb_per_day
    hub_w = {}
    if hub:
        for (a, b), v in und.items():
            other = b if a == hub else a if b == hub else None
            if other in mset:
                hub_w[other] = v
    return Problem(
        estate,
        cfg,
        movable,
        strategy,
        effort,
        nservers,
        team,
        allowed,
        pilot_ok,
        weights,
        dict(adj),
        dict(gb),
        hub,
        hub_w,
    )


class _State:
    """Wave loads for incremental feasibility checks."""

    def __init__(self, p: Problem):
        self.p = p
        self.effort = defaultdict(float)
        self.servers = defaultdict(int)
        self.team = defaultdict(int)  # (wave, team)
        self.where: dict[str, int] = {}

    def fits(self, apps: list[str], w: int) -> bool:
        p = self.p
        if any(w not in p.allowed[a] for a in apps):
            return False
        if self.effort[w] + sum(p.effort[a] for a in apps) > p.wave_effort_cap(w) + 1e-9:
            return False
        if self.servers[w] + sum(p.nservers[a] for a in apps) > p.cfg.max_servers:
            return False
        need = defaultdict(int)
        for a in apps:
            need[p.team[a]] += 1
        return all(self.team[(w, t)] + n <= p.team_cap(t) for t, n in need.items())

    def place(self, a: str, w: int) -> None:
        self.where[a] = w
        self.effort[w] += self.p.effort[a]
        self.servers[w] += self.p.nservers[a]
        self.team[(w, self.p.team[a])] += 1

    def remove(self, a: str) -> None:
        w = self.where.pop(a)
        self.effort[w] -= self.p.effort[a]
        self.servers[w] -= self.p.nservers[a]
        self.team[(w, self.p.team[a])] -= 1


def _first_fit(p: Problem, order: list[str]) -> dict[str, int]:
    st = _State(p)
    for a in order:
        for w in range(1, p.cfg.n_waves + 1):
            if st.fits([a], w):
                st.place(a, w)
                break
    return st.where


def plan_alphabetical(p: Problem) -> dict[str, int]:
    return _first_fit(p, sorted(p.movable, key=lambda a: p.estate.apps[a].name))


def plan_by_business_unit(p: Problem) -> dict[str, int]:
    return _first_fit(p, sorted(p.movable, key=lambda a: (p.estate.apps[a].business_unit, p.estate.apps[a].name)))


def _clusters(p: Problem) -> list[list[str]]:
    """Capacity-constrained agglomeration: merge along the heaviest edges while the merged group still fits in one
    wave (effort, servers, team capacity) and its members share at least one allowed wave."""
    parent = {a: a for a in p.movable}
    members = {a: [a] for a in p.movable}
    allowed = {a: set(p.allowed[a]) - {1} for a in p.movable}
    effort = dict(p.effort)
    servers = dict(p.nservers)
    teams = {a: {p.team[a]: 1} for a in p.movable}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    cap = p.cfg.max_effort * p.cfg.cluster_fill
    for (a, b), _w in sorted(p.weights.items(), key=lambda kv: -kv[1]):
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        inter = allowed[ra] & allowed[rb]
        if (
            not inter
            or effort[ra] + effort[rb] > cap
            or servers[ra] + servers[rb] > p.cfg.max_servers * p.cfg.cluster_fill
        ):
            continue
        merged_teams = dict(teams[ra])
        for t, n in teams[rb].items():
            merged_teams[t] = merged_teams.get(t, 0) + n
        if any(n > p.team_cap(t) for t, n in merged_teams.items()):
            continue
        parent[rb] = ra
        members[ra] += members.pop(rb)
        allowed[ra], effort[ra], servers[ra], teams[ra] = (
            inter,
            effort[ra] + effort[rb],
            servers[ra] + servers[rb],
            merged_teams,
        )
    return [sorted(m) for m in members.values()]


def plan_optimized(p: Problem, hub_wave: int | None = None) -> dict[str, int]:
    """Greedy partitioning. If hub_wave is given, the shared database is pinned there and pulls its consumers."""
    clusters = _clusters(p)
    st = _State(p)
    pinned = {p.hub: hub_wave} if p.hub and hub_wave else {}
    adj = {a: dict(nb) for a, nb in p.adj.items()}
    if pinned:
        for a, v in p.hub_weights.items():
            adj.setdefault(a, {})[p.hub] = v

    def wave_of(b: str) -> int | None:
        return st.where.get(b, pinned.get(b))

    def external(c: list[str]) -> float:
        cs = set(c)
        return sum(v for a in c for b, v in adj.get(a, {}).items() if b not in cs) + sum(
            p.hub_weights.get(a, 0.0) for a in c if not pinned
        )

    # pilot wave: low risk, loosely coupled groups first
    pilots = [c for c in clusters if all(p.pilot_ok[a] and 1 in p.allowed[a] for a in c)]
    pilots.sort(key=lambda c: (external(c) / len(c), -len(c)))
    for c in pilots:
        if st.fits(c, 1):
            for a in c:
                st.place(a, 1)
    singles = [
        a
        for a in p.movable
        if a not in st.where
        and p.pilot_ok[a]
        and 1 in p.allowed[a]
        and sum(adj.get(a, {}).values()) <= p.cfg.pilot_single_max_weight
    ]
    for a in sorted(singles, key=lambda a: (sum(adj.get(a, {}).values()), a)):
        if st.fits([a], 1):
            st.place(a, 1)
    rest = [r for r in ([a for a in c if a not in st.where] for c in clusters) if r]
    n = p.cfg.n_waves

    def affinity(c: list[str], w: int) -> tuple[float, float]:
        same = dist = 0.0
        for a in c:
            for b, v in adj.get(a, {}).items():
                wb = wave_of(b)
                if wb is None:
                    continue
                if wb == w:
                    same += v
                dist += v * abs(wb - w)
        return same, dist

    rest.sort(key=lambda c: (len(set.intersection(*(p.allowed[a] for a in c))), -sum(p.effort[a] for a in c)))
    leftovers = []
    for c in rest:
        options = [w for w in range(2, n + 1) if st.fits(c, w)]
        if not options:
            leftovers.extend(c)
            continue
        best = max(options, key=lambda w: (affinity(c, w)[0], -affinity(c, w)[1], -w))
        for a in c:
            st.place(a, best)
    for a in sorted(leftovers, key=lambda a: len(p.allowed[a])):
        options = [w for w in range(1, n + 1) if st.fits([a], w)]
        if options:
            st.place(a, max(options, key=lambda w: (affinity([a], w)[0], -affinity([a], w)[1], -w)))

    # local refinement: single moves that lower the cut and keep every constraint
    for _ in range(p.cfg.refine_passes):
        moved = 0
        for a in sorted(st.where):
            cur = st.where[a]
            if cur == 1:
                continue  # pilots stay put: wave 1 is chosen for low risk, not for traffic
            nb = adj.get(a, {})
            if not nb:
                continue
            gain_by_wave = defaultdict(float)
            for b, v in nb.items():
                wb = wave_of(b)
                if wb is not None:
                    gain_by_wave[wb] += v
            here = gain_by_wave.get(cur, 0.0)
            best_w, best_gain = cur, 1e-9
            for w, g in gain_by_wave.items():
                if w == cur or g - here <= best_gain:
                    continue
                st.remove(a)
                ok = st.fits([a], w)
                st.place(a, cur)
                if ok:
                    best_w, best_gain = w, g - here
            if best_w != cur:
                st.remove(a)
                st.place(a, best_w)
                moved += 1
        if not moved:
            break
    return st.where


def hub_waves(p: Problem) -> list[int]:
    if not p.hub:
        return []
    hub = p.estate.apps[p.hub]
    return [w for w in range(2, p.cfg.n_waves + 1) if p.wave_month(w) not in hub.freeze_months]


def place_hub(p: Problem, where: dict[str, int]) -> int | None:
    """Cut the shared database over at the traffic-weighted median wave of its consumers, outside its freeze."""
    ok = hub_waves(p)
    cost = {w: sum(v * abs(where.get(a, p.cfg.n_waves) - w) for a, v in p.hub_weights.items()) for w in ok}
    return min(ok, key=lambda w: (cost[w], w)) if ok else None


def evaluate_plan(p: Problem, where: dict[str, int], hub_wave: int | None) -> dict:
    cut = wan_gb = 0.0
    split_edges = latency_splits = 0
    for (a, b), v in p.weights.items():
        wa, wb = where.get(a), where.get(b)
        if wa is None or wb is None or wa == wb:
            continue
        cut += v
        split_edges += 1
        wan_gb += p.gb_per_day.get((a, b), 0.0) * abs(wa - wb) * p.cfg.wave_days
        if p.estate.apps[a].latency_sensitive or p.estate.apps[b].latency_sensitive:
            latency_splits += 1
    hub_cut = hub_gb = 0.0
    hub_split = 0
    if p.hub and hub_wave:
        for a, v in p.hub_weights.items():
            wa = where.get(a)
            if wa is not None and wa != hub_wave:
                hub_cut += v
                hub_split += 1
                key = (a, p.hub) if a < p.hub else (p.hub, a)
                hub_gb += p.gb_per_day.get(key, 0.0) * abs(wa - hub_wave) * p.cfg.wave_days
    total = sum(p.weights.values())
    return {
        "cut_weight": round(cut, 2),
        "cut_share": round(cut / total, 4) if total else 0.0,
        "split_edges": split_edges,
        "edges": len(p.weights),
        "latency_sensitive_splits": latency_splits,
        "wan_gb": round(wan_gb, 1),
        "hub_wave": hub_wave,
        "hub_cut_weight": round(hub_cut, 2),
        "hub_split_consumers": hub_split,
        "hub_wan_gb": round(hub_gb, 1),
        "total_cut_weight": round(cut + hub_cut, 2),
        "total_wan_gb": round(wan_gb + hub_gb, 1),
        "scheduled": len(where),
        "unscheduled": len(p.movable) - len(where),
        "waves_used": len(set(where.values())),
    }


def violations(p: Problem, where: dict[str, int]) -> list[str]:
    """Every hard-constraint breach in an assignment. Empty means the plan is valid."""
    out = []
    eff, srv, team = defaultdict(float), defaultdict(int), defaultdict(int)
    for a, w in where.items():
        if w not in p.allowed[a]:
            out.append(f"{a} not allowed in wave {w}")
        eff[w] += p.effort[a]
        srv[w] += p.nservers[a]
        team[(w, p.team[a])] += 1
    for w, e in eff.items():
        if e > p.wave_effort_cap(w) + 1e-9:
            out.append(f"wave {w} effort {e} over {p.wave_effort_cap(w)}")
    for w, s in srv.items():
        if s > p.cfg.max_servers:
            out.append(f"wave {w} servers {s} over {p.cfg.max_servers}")
    for (w, t), n in team.items():
        if n > p.team_cap(t):
            out.append(f"wave {w} team {t} has {n} apps, capacity {p.team_cap(t)}")
    return out


PLANNERS = {"optimized": plan_optimized, "alphabetical": plan_alphabetical, "business_unit": plan_by_business_unit}
LABELS = {
    "optimized": "Graph partitioning (greedy merge + refinement)",
    "alphabetical": "Alphabetical",
    "business_unit": "By business unit",
}


@dataclass
class WavePlan:
    method: str
    where: dict[str, int]
    hub_wave: int | None
    metrics: dict
    waves: list[dict]


def build_plan(p: Problem, method: str = "optimized") -> WavePlan:
    if method == "optimized" and p.hub:
        # try each legal cutover wave for the shared database, keep the plan with the lowest total cut
        best = None
        for hw in hub_waves(p):
            where = plan_optimized(p, hw)
            m = evaluate_plan(p, where, hw)
            key = (m["unscheduled"], m["total_cut_weight"])
            if best is None or key < best[0]:
                best = (key, where, hw, m)
        _, where, hub_wave, metrics = best
    else:
        where = PLANNERS[method](p)
        hub_wave = place_hub(p, where)
        metrics = evaluate_plan(p, where, hub_wave)
    waves = []
    for w in range(1, p.cfg.n_waves + 1):
        apps = sorted(a for a, x in where.items() if x == w)
        start = p.wave_start(w)
        waves.append(
            {
                "wave": w,
                "label": f"{MONTHS[start.month - 1]} {start.year}",
                "start": str(start),
                "pilot": w == 1,
                "apps": apps,
                "effort": round(sum(p.effort[a] for a in apps), 1),
                "servers": sum(p.nservers[a] for a in apps),
                "includes_shared_db": hub_wave == w,
                "effort_cap": p.wave_effort_cap(w),
            }
        )
    return WavePlan(method, where, hub_wave, metrics, waves)


def compare(p: Problem) -> dict:
    plans = {m: build_plan(p, m) for m in PLANNERS}
    base = plans["business_unit"].metrics["total_cut_weight"]
    rows = []
    for m, plan in plans.items():
        mt = plan.metrics
        rows.append(
            dict(
                mt,
                method=m,
                label=LABELS[m],
                reduction_vs_bu=round(1 - mt["total_cut_weight"] / base, 4) if base else 0.0,
            )
        )
    return {"plans": plans, "rows": rows}
