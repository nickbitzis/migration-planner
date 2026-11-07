"""Command line.

uv run migplan serve                 # API and UI on http://127.0.0.1:8821
uv run migplan plan --out reports    # full plan on the sample estate: waves.csv, migration-plan.md, plan.json
uv run migplan estate --out data     # write the synthetic inventory, servers, and flows as CSV
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict
from pathlib import Path


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: " ".join(map(str, v)) if isinstance(v, list) else v for k, v in r.items()})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="migplan")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8821")))
    p = sub.add_parser("plan")
    p.add_argument("--out", default="reports")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--summary", help="append the wave summary as Markdown to this file (e.g. $GITHUB_STEP_SUMMARY)")
    p.add_argument("--gate", action="store_true", help="exit 1 if the optimized plan does not beat both naive plans")
    est = sub.add_parser("estate")
    est.add_argument("--out", default="data")
    est.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("migplan.app:create_app", factory=True, host=args.host, port=args.port, access_log=False)
        return 0

    from .export import comparison_table, plan_markdown, wave_table, waves_csv
    from .plan import Planner
    from .synth import SynthConfig, generate

    estate = generate(SynthConfig(seed=args.seed))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.cmd == "estate":
        _write_csv(out / "applications.csv", [{k: v for k, v in a.to_dict().items()} for a in estate.apps.values()])
        _write_csv(out / "servers.csv", [asdict(s) for s in estate.servers.values()])
        _write_csv(out / "flows.csv", [asdict(f) for f in estate.flows])
        print(f"wrote {len(estate.apps)} apps, {len(estate.servers)} servers, {len(estate.flows)} flows to {out}")
        return 0

    pl = Planner(estate)
    (out / "waves.csv").write_text(waves_csv(pl))
    (out / "migration-plan.md").write_text(plan_markdown(pl))
    facts = pl.facts()
    (out / "plan.json").write_text(
        json.dumps(
            {
                "facts": facts,
                "comparison": pl.comparison,
                "tco": {k: v for k, v in pl.tco.items() if not k.endswith("monthly")},
            },
            indent=2,
        )
        + "\n"
    )
    md = "\n".join(
        [
            f"## Migration plan: {estate.company}",
            "",
            f"{facts['apps']} apps, {facts['servers']} servers, {facts['dependencies_discovered']} dependencies "
            f"discovered ({facts['undocumented_dependencies']} undocumented). Strategy mix: "
            + ", ".join(f"{k} {v}" for k, v in facts["strategy_mix"].items())
            + ".",
            "",
            "### Wave plan comparison",
            "",
            comparison_table(pl.comparison),
            "",
            "### Waves (optimized plan)",
            "",
            wave_table(pl),
            "",
            f"NPV ${facts['npv_usd']:,}, break-even month {facts['break_even_month']}, "
            f"one time ${facts['one_time_usd']:,}, {facts['risks']} risks ({facts['high_risks']} high).",
            "",
        ]
    )
    print(md)
    if args.summary:
        with open(args.summary, "a") as f:
            f.write(md + "\n")
    if args.gate:
        rows = {r["method"]: r["total_cut_weight"] for r in pl.comparison}
        if not (rows["optimized"] < rows["business_unit"] and rows["optimized"] < rows["alphabetical"]):
            print("gate failed: optimized plan does not beat the naive plans")
            return 1
        if pl.plan.metrics["unscheduled"]:
            print("gate failed: unscheduled apps")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
