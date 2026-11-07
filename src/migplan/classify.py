"""Explainable 6R classification: YAML rules add scores per strategy, every score change carries a reason."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from .discovery import Discovery
from .models import DB_COMMERCIAL, OS_EOL, Estate, is_eol

STRATEGIES = ("retain", "retire", "repurchase", "refactor", "replatform", "rehost")
DEFAULT_RULES = Path(__file__).parent / "rules.yaml"

FEATURE_DOCS = {
    "platform": "x86, unix (Solaris, AIX), or mainframe",
    "os_eol": "OS is past end of support at plan start",
    "os_eol_by_plan_end": "OS reaches end of support before the program ends (plan start + 18 months)",
    "db_commercial": "Oracle, SQL Server, or DB2",
    "dependents": "apps that call this one (discovered from flows)",
    "dependencies": "apps this one calls (discovered from flows)",
    "calls_mainframe_online": "makes online (MQ) calls to the mainframe, not just batch files",
    "duplicate": "inventory marks another app as doing the same job",
    "team_cloud_skill": "owning team cloud skill, 0 to 3",
    "team_container_skill": "owning team container skill, 0 to 3",
}


class RuleError(ValueError):
    pass


def features(app_id: str, estate: Estate, disc: Discovery | None) -> dict[str, Any]:
    app = estate.apps[app_id]
    team = estate.teams.get(app.owner_team)
    plan_end = date(estate.plan_start.year + 1, min(12, estate.plan_start.month + 6), 1)
    platform = "mainframe" if app.os.startswith("z/OS") else "unix" if app.os.startswith(("AIX", "Solaris")) else "x86"
    dependents = sorted({a for (a, b) in disc.edges if b == app_id}) if disc else []
    dependencies = sorted({b for (a, b) in disc.edges if a == app_id}) if disc else []
    mf_online = bool(disc) and any(
        estate.apps[b].kind == "mainframe" and 1414 in e.ports for (a, b), e in disc.edges.items() if a == app_id
    )
    servers = estate.servers_of(app_id)
    return {
        "id": app.id,
        "name": app.name,
        "business_unit": app.business_unit,
        "kind": app.kind,
        "os": app.os,
        "platform": platform,
        "os_eol": is_eol(app.os, estate.plan_start),
        "os_eol_by_plan_end": is_eol(app.os, plan_end),
        "os_eol_date": str(OS_EOL.get(app.os, "")),
        "db_engine": app.db_engine,
        "db_commercial": app.db_engine in DB_COMMERCIAL,
        "cots": app.cots,
        "vendor_product": app.vendor_product or "none",
        "saas_equivalent": app.saas_equivalent,
        "monthly_users": app.monthly_users,
        "years_since_change": app.years_since_change,
        "deploys_per_year": app.deploys_per_year,
        "criticality": app.criticality,
        "business_value": app.business_value,
        "latency_sensitive": app.latency_sensitive,
        "compliance": list(app.compliance),
        "data_gb": app.data_gb,
        "tech_stack": app.tech_stack,
        "owner_team": app.owner_team,
        "team_cloud_skill": team.cloud_skill if team else 0,
        "team_container_skill": team.container_skill if team else 0,
        "dependents": len(dependents),
        "dependencies": len(dependencies),
        "calls_mainframe_online": mf_online,
        "duplicate": app.duplicate_of is not None,
        "duplicate_of_name": estate.apps[app.duplicate_of].name if app.duplicate_of else "",
        "servers": len(servers),
        "hardcoded_ips": len(app.hardcoded_ips),
    }


_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: b in a,
}


def evaluate(cond: dict, feats: dict[str, Any]) -> bool:
    if "all" in cond:
        return all(evaluate(c, feats) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, feats) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], feats)
    if "field" not in cond:
        raise RuleError(f"condition needs field, all, any, or not: {cond}")
    name = cond["field"]
    if name not in feats:
        raise RuleError(f"unknown field {name!r}")
    ops = [k for k in cond if k != "field"]
    if len(ops) != 1 or ops[0] not in _OPS:
        raise RuleError(f"condition on {name!r} needs exactly one of {sorted(_OPS)}")
    return _OPS[ops[0]](feats[name], cond[ops[0]])


@dataclass
class Override:
    app_id: str
    strategy: str
    by: str
    reason: str
    at: str = ""
    source: str = "api"

    def __post_init__(self):
        if self.strategy not in STRATEGIES:
            raise RuleError(f"unknown strategy {self.strategy!r}")
        if not self.by.strip() or not self.reason.strip():
            raise RuleError("an override needs who (by) and why (reason)")
        self.at = self.at or datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Rules:
    strategies: tuple[str, ...]
    base: dict[str, float]
    rules: list[dict]
    overrides: list[Override] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path | None = None, text: str | None = None) -> Rules:
        data = yaml.safe_load(text if text is not None else Path(path or DEFAULT_RULES).read_text())
        strategies = tuple(data.get("strategies", STRATEGIES))
        if set(strategies) != set(STRATEGIES):
            raise RuleError("strategies must be exactly the six Rs")
        seen = set()
        for r in data.get("rules", []):
            for key in ("id", "when", "scores", "reason"):
                if key not in r:
                    raise RuleError(f"rule {r.get('id', '?')} is missing {key}")
            if r["id"] in seen:
                raise RuleError(f"duplicate rule id {r['id']}")
            seen.add(r["id"])
            bad = set(r["scores"]) - set(STRATEGIES)
            if bad:
                raise RuleError(f"rule {r['id']} scores unknown strategies {sorted(bad)}")
        ovs = [Override(**o, source="config") for o in data.get("overrides", []) or []]
        return cls(strategies, {k: float(v) for k, v in (data.get("base") or {}).items()}, data.get("rules", []), ovs)


@dataclass
class Classification:
    app_id: str
    strategy: str  # final, after any override
    computed: str  # what the rules chose
    scores: dict[str, float]
    reasons: list[dict]  # {rule, text, scores}
    confidence: float  # (top - runner up) / top, 0..1
    override: Override | None = None
    main_reason: str = ""  # the rule that added the most to the winning strategy

    def to_dict(self) -> dict:
        d = asdict(self)
        d["overridden"] = self.override is not None
        return d


def classify_app(feats: dict[str, Any], rules: Rules) -> Classification:
    scores = {s: rules.base.get(s, 0.0) for s in rules.strategies}
    reasons = []
    for r in rules.rules:
        if evaluate(r["when"], feats):
            for s, v in r["scores"].items():
                scores[s] += float(v)
            try:
                text = r["reason"].format(**feats)
            except (KeyError, IndexError) as exc:
                raise RuleError(f"rule {r['id']} reason uses unknown field {exc}") from exc
            reasons.append({"rule": r["id"], "text": text, "scores": r["scores"]})
    ranked = sorted(rules.strategies, key=lambda s: (-scores[s], rules.strategies.index(s)))
    top, second = scores[ranked[0]], scores[ranked[1]]
    conf = 0.0 if top <= 0 else max(0.0, min(1.0, (top - second) / top))
    if not reasons:
        reasons.append({"rule": "default", "text": "No rule fired; rehost is the default", "scores": {}})
    win = ranked[0]
    best = max(reasons, key=lambda r: float(r["scores"].get(win, 0)))
    main = (
        best["text"]
        if float(best["scores"].get(win, 0)) > 0
        else f"{win.capitalize()} is the default and no rule scored higher"
    )
    return Classification(
        feats["id"], win, win, {k: round(v, 2) for k, v in scores.items()}, reasons, round(conf, 3), main_reason=main
    )


def classify(
    estate: Estate, disc: Discovery | None, rules: Rules, overrides: dict[str, Override] | None = None
) -> dict[str, Classification]:
    merged = {o.app_id: o for o in rules.overrides}
    merged.update(overrides or {})
    out = {}
    for app_id in sorted(estate.apps):
        c = classify_app(features(app_id, estate, disc), rules)
        o = merged.get(app_id)
        if o:
            c.strategy, c.override = o.strategy, o
        out[app_id] = c
    return out
