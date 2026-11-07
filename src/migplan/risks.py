"""Risk register generated from computed facts. Each risk has likelihood and impact (1 to 5) and a mitigation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .classify import Classification
from .discovery import Discovery
from .models import Estate, is_eol
from .waves import MOVABLE, Problem, WavePlan

DB_PORTS = {1521, 1433, 5432, 3306, 50000}


@dataclass
class Risk:
    id: str
    category: str
    title: str
    apps: list[str]
    wave: int | None
    likelihood: int
    impact: int
    mitigation: str
    owner: str

    @property
    def score(self) -> int:
        return self.likelihood * self.impact

    def to_dict(self) -> dict:
        return asdict(self) | {"score": self.score}


def generate_risks(
    estate: Estate, disc: Discovery, classes: dict[str, Classification], problem: Problem, plan: WavePlan
) -> list[Risk]:
    apps = estate.apps
    where = dict(plan.where)
    if problem.hub and plan.hub_wave:
        where[problem.hub] = plan.hub_wave
    strat = {a: c.strategy for a, c in classes.items()}
    risks: list[Risk] = []

    def add(category, title, app_ids, wave, lik, imp, mitigation, owner):
        risks.append(Risk("", category, title, sorted(app_ids), wave, lik, imp, mitigation, owner))

    def wave_label(a):
        w = where.get(a)
        return f"wave {w}" if w else ("stays on premises" if strat[a] == "retain" else strat[a])

    # latency sensitive app split from a database it talks to
    for (a, b), e in sorted(disc.edges.items()):
        if not apps[a].latency_sensitive or not (e.ports & DB_PORTS):
            continue
        if strat[a] not in MOVABLE or strat[b] == "retire":
            continue
        wa, wb = where.get(a), where.get(b)
        if wa == wb:
            continue
        add(
            "latency",
            f"{apps[a].name} ({wave_label(a)}) is latency sensitive and its database in "
            f"{apps[b].name} ({wave_label(b)}) moves separately; {e.conns_per_day:,.0f} connections a day "
            f"would cross the WAN",
            [a, b],
            min(x for x in (wa, wb) if x) if (wa or wb) else None,
            4,
            4 if apps[a].criticality <= 2 else 3,
            f"Move both in the same wave, or keep a replica of the database next to {apps[a].name} until "
            f"{apps[b].name} moves",
            apps[a].owner_team,
        )

    # shared database cutover
    if problem.hub:
        hub = apps[problem.hub]
        consumers = sorted(problem.hub_weights)
        undoc = [d["src"] for d in disc.undocumented if d["dst"] == hub.id and d["src"] in problem.hub_weights]
        split = sum(1 for c in consumers if where.get(c) != plan.hub_wave)
        add(
            "shared database",
            f"{hub.name} serves {len(consumers)} migrating apps ({len(undoc)} of them not in "
            f"the CMDB); {split} cut over in a different wave than the database",
            [hub.id] + consumers,
            plan.hub_wave,
            4,
            5,
            "Run log based replication to the managed database from wave 2, point every consumer at a DNS alias, "
            "rehearse the cutover twice, and keep the on premises copy writable for rollback for two weeks",
            hub.owner_team,
        )

    # mainframe batch interface
    mf = next((x for x in apps.values() if x.kind == "mainframe"), None)
    if mf:
        batch = [(a, e) for (a, b), e in disc.edges.items() if b == mf.id and 1364 in e.ports]
        if batch:
            gb = sum(e.gb_per_day for _, e in batch)
            add(
                "mainframe",
                f"{len(batch)} apps exchange nightly batch files with {mf.name} ({gb:,.0f} GB a night); "
                "after they move, every file crosses the private link inside the batch window",
                [a for a, _ in batch],
                None,
                3,
                4,
                "Measure the batch window on the private link before wave 2, size the link for the nightly peak, "
                "and keep file transfer retry and checkpoint settings",
                mf.owner_team,
            )

    # undocumented dependencies
    undoc_by_app = defaultdict(list)
    for d in disc.undocumented:
        undoc_by_app[d["src"]].append(d)
    for a, ds in sorted(undoc_by_app.items()):
        if strat[a] not in MOVABLE:
            continue
        names = ", ".join(apps[d["dst"]].name for d in ds[:3])
        split = [d for d in ds if where.get(d["dst"]) != where.get(a)]
        noun = "dependency" if len(ds) == 1 else "dependencies"
        add(
            "discovery",
            f"{apps[a].name} has {len(ds)} {noun} seen only in network flows ({names}); "
            f"{len(split)} split across waves",
            [a] + [d["dst"] for d in ds],
            where.get(a),
            4 if split else 2,
            3 if apps[a].criticality > 2 else 4,
            "Confirm each with the owning team, add it to the CMDB, and include it in the wave test plan",
            apps[a].owner_team,
        )

    # hardcoded IPs
    for a in sorted(apps):
        if apps[a].hardcoded_ips and strat[a] in ("rehost", "replatform", "refactor"):
            add(
                "configuration",
                f"{apps[a].name} has IP literals in its config ({', '.join(apps[a].hardcoded_ips)}); "
                "they change on migration",
                [a],
                where.get(a),
                4,
                3,
                "Replace with DNS names before the wave and rescan the config",
                apps[a].owner_team,
            )

    # compliance scope: first wave that brings each tag into the cloud
    for tag, text in (
        ("PCI", "cardholder data"),
        ("PHI", "health data"),
        ("PII", "personal data"),
        ("SOX", "financial reporting systems"),
    ):
        tagged = [a for a in where if tag in apps[a].compliance]
        if tagged:
            first = min(where[a] for a in tagged)
            add(
                "compliance",
                f"{tag}: {len(tagged)} apps bring {text} into the cloud, starting in wave {first}",
                tagged,
                first,
                3,
                5 if tag in ("PCI", "PHI") else 4,
                f"Separate {tag} account with its own guardrails, control evidence mapped before wave {first}, "
                "and an assessor walkthrough of the landing zone",
                "security",
            )

    # skills gap
    for t in sorted(estate.teams.values(), key=lambda t: t.name):
        owned = [a for a in where if apps[a].owner_team == t.name and strat[a] in ("replatform", "refactor")]
        if t.cloud_skill <= 1 and owned:
            add(
                "skills",
                f"Team {t.name} (cloud skill {t.cloud_skill} of 3) owns {len(owned)} replatform or refactor moves",
                owned,
                min(where[a] for a in owned),
                4,
                3,
                "Training before its first wave, pair with platform-eng on the first two moves, and put its "
                "simplest app first",
                t.name,
            )

    # rehost onto an OS that goes out of support
    for a in sorted(where):
        if strat[a] == "rehost" and is_eol(apps[a].os, estate.plan_start.replace(year=estate.plan_start.year + 2)):
            add(
                "lifecycle",
                f"{apps[a].name} is rehosted on {apps[a].os}, which is out of support within two years",
                [a],
                where[a],
                3,
                3,
                "Upgrade the OS on the cloud copy within two quarters of cutover",
                apps[a].owner_team,
            )

    # something still calls an app planned for retirement
    for (a, b), e in sorted(disc.edges.items()):
        if strat[b] == "retire" and strat[a] != "retire":
            add(
                "retirement",
                f"{apps[a].name} still calls {apps[b].name}, which is planned for retirement "
                f"({e.conns_per_day:,.0f} connections a day)",
                [a, b],
                where.get(a),
                4,
                4 if apps[a].criticality <= 2 else 3,
                f"Repoint {apps[a].name} first, or move the retirement after its wave",
                apps[b].owner_team,
            )

    # servers that are not in the inventory
    for u in disc.unknown_endpoints:
        add(
            "discovery",
            f"{len(u['apps'])} apps talk to {u['ip']} on port {u['ports'][0]}, an address that is not "
            f"in the CMDB ({u['bytes'] / 1e9:,.0f} GB in {estate.observation_days} days)",
            u["apps"],
            None,
            4,
            4,
            "Find the owner, add it to the inventory, and classify it before the first dependent app moves",
            "infrastructure",
        )

    # freeze squeeze
    for a in sorted(problem.movable):
        n_ok = len(problem.allowed[a])
        if n_ok <= 6:
            add(
                "schedule",
                f"{apps[a].name} can only move in {n_ok} of {problem.cfg.n_waves} waves "
                "(change freezes, team availability)",
                [a],
                where.get(a),
                2,
                3,
                "Book the wave early; a slip pushes it out by several months",
                apps[a].owner_team,
            )

    if disc.stale_documented:
        add(
            "discovery",
            f"{len(disc.stale_documented)} documented dependencies had no traffic in {estate.observation_days} days",
            sorted({d["src"] for d in disc.stale_documented}),
            None,
            2,
            2,
            "Check for monthly or quarterly jobs before removing them from the CMDB; extend the flow capture "
            "over a month end",
            "architecture",
        )

    risks.sort(key=lambda r: (-r.score, r.category, r.title))
    for i, r in enumerate(risks, 1):
        r.id = f"R-{i:03d}"
    return risks
