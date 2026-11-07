"""Exports: the wave plan as CSV and the whole plan as a Markdown document."""

from __future__ import annotations

import csv
import io

from .plan import Planner
from .summary import offline_summary
from .waves import LABELS

CSV_FIELDS = [
    "wave",
    "wave_start",
    "app_id",
    "app_name",
    "business_unit",
    "owner_team",
    "strategy",
    "overridden",
    "criticality",
    "servers",
    "effort",
    "compliance",
    "latency_sensitive",
    "pilot",
]


def waves_csv(pl: Planner) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    rows = []
    for wave in pl.plan.waves:
        ids = list(wave["apps"]) + ([pl.problem.hub] if wave["includes_shared_db"] else [])
        for a in ids:
            app, c = pl.estate.apps[a], pl.classes[a]
            rows.append(
                {
                    "wave": wave["wave"],
                    "wave_start": wave["start"],
                    "app_id": a,
                    "app_name": app.name,
                    "business_unit": app.business_unit,
                    "owner_team": app.owner_team,
                    "strategy": c.strategy,
                    "overridden": c.override is not None,
                    "criticality": app.criticality,
                    "servers": len(app.server_ids),
                    "effort": pl.problem.effort.get(a, 0),
                    "compliance": " ".join(app.compliance),
                    "latency_sensitive": app.latency_sensitive,
                    "pilot": wave["pilot"],
                }
            )
    w.writerows(rows)
    return buf.getvalue()


def comparison_table(rows: list[dict]) -> str:
    out = [
        "| Plan | Cross-wave traffic (weight/day) | Of which shared DB | Split dependencies | "
        "Latency sensitive splits | WAN GB during migration | vs by business unit |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        vs = "baseline" if r["method"] == "business_unit" else format(-r["reduction_vs_bu"], "+.0%")
        out.append(
            f"| {LABELS[r['method']]} | {r['total_cut_weight']:,.0f} | {r['hub_cut_weight']:,.0f} | "
            f"{r['split_edges']} of {r['edges']} | {r['latency_sensitive_splits']} | "
            f"{r['total_wan_gb']:,.0f} | {vs} |"
        )
    return "\n".join(out)


def wave_table(pl: Planner) -> str:
    out = ["| Wave | Month | Apps | Effort | Servers | Notes |", "|---|---|---|---|---|---|"]
    for w in pl.plan.waves:
        notes = []
        if w["pilot"]:
            notes.append("pilot")
        if w["includes_shared_db"]:
            notes.append(f"{pl.estate.apps[pl.problem.hub].name} cutover")
        out.append(
            f"| {w['wave']} | {w['label']} | {len(w['apps'])} | {w['effort']:g} of {w['effort_cap']:g} | "
            f"{w['servers']} | {', '.join(notes)} |"
        )
    return "\n".join(out)


def plan_markdown(pl: Planner) -> str:
    f = pl.facts()
    t = pl.tco
    a = t["assumptions"]
    lines = [
        f"# Migration plan: {pl.estate.company}",
        "",
        "## Executive summary",
        "",
        offline_summary(f),
        "",
        "## Wave comparison",
        "",
        comparison_table(pl.comparison),
        "",
        "Cross-wave traffic is the edge weight (GB per day plus 1 per 10,000 connections per day) between apps "
        "in different waves. WAN GB multiplies each split edge's daily volume by the months between its two "
        "waves.",
        "",
        "## Waves",
        "",
        wave_table(pl),
        "",
    ]
    for w in pl.plan.waves:
        names = [f"{pl.estate.apps[x].name} ({pl.classes[x].strategy})" for x in w["apps"]]
        lines.append(f"- **Wave {w['wave']} ({w['label']})**: {', '.join(names) or 'none'}")
    nm = pl.not_moving()
    lines += [
        "",
        f"Not moving: {len(nm['retire'])} retired, {len(nm['retain'])} retained.",
        "",
        "## Portfolio (6R)",
        "",
        "| App | Strategy | Wave | Main reason |",
        "|---|---|---|---|",
    ]
    for row in pl.portfolio():
        reason = (
            row["override"]["reason"] + f" (override by {row['override']['by']})"
            if row["override"]
            else row["main_reason"]
        )
        lines.append(f"| {row['id']} {row['name']} | {row['strategy']} | {row['wave'] or ''} | {reason} |")
    lines += ["", "## TCO (5 years)", "", "| Year | Stay on premises | Migrate | Savings |", "|---|---|---|---|"]
    for y in t["yearly"]:
        lines.append(f"| {y['year']} | ${y['onprem']:,} | ${y['migrate']:,} | ${y['savings']:,} |")
    lines += [
        "",
        f"- One time cost: ${t['one_time_total']:,}",
        f"- NPV at {a['discount_rate']:.0%}: ${t['npv']:,}",
        f"- Break-even month: {t['break_even_month']} ({t['break_even_date']})",
        f"- Hardware refresh avoided: ${t['refresh_capex_avoided']:,}",
        f"- Steady state annual savings: ${t['steady_state_annual_savings']:,}",
        "",
        "### Assumptions",
        "",
    ]
    for k, v in a.items():
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Risk register", "", "| ID | Score | Category | Risk | Mitigation |", "|---|---|---|---|---|"]
    for r in pl.risks:
        lines.append(f"| {r.id} | {r.score} ({r.likelihood}x{r.impact}) | {r.category} | {r.title} | {r.mitigation} |")
    return "\n".join(lines) + "\n"
