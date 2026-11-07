"""Executive summary of the plan, drafted only from computed facts.

The offline provider fills a template. The Claude provider sends the same facts as JSON and asks for prose; every
number in its answer is then checked against the facts, and the draft is flagged if any number is not found there.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

MODEL = os.environ.get("MIGPLAN_MODEL", "claude-opus-5-5")
SYSTEM = (
    "You write executive summaries of cloud migration plans for a CIO. Use only the facts in the JSON you are "
    "given. Do not add numbers, vendors, dates, or claims that are not in the facts. Plain English, short complete "
    "sentences, no marketing language, no dashes as punctuation. Four short paragraphs: scope and approach, wave "
    "plan, money, top risks."
)


def _usd(x: float) -> str:
    return f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


def offline_summary(f: dict[str, Any]) -> str:
    mix = ", ".join(f"{n} {k}" for k, n in sorted(f["strategy_mix"].items(), key=lambda kv: -kv[1]))
    be = (
        f"Break-even is in month {f['break_even_month']} ({f['break_even_date']})."
        if f["break_even_month"]
        else "The plan does not break even inside five years."
    )
    risks = "; ".join(f"{r['id']} {r['title']} (score {r['score']})" for r in f["top_risks"][:3])
    return "\n\n".join(
        [
            f"{f['company']} runs {f['apps']} applications on {f['servers']} servers in its data center. Flow analysis "
            f"found {f['dependencies_discovered']} application dependencies, {f['undocumented_dependencies']} of which "
            f"were missing from the CMDB, plus {f['unknown_endpoints']} servers that are not in the inventory at all. "
            f"The 6R rules place the portfolio as {mix}. People overrode {f['overrides']} of those decisions.",
            f"The migration runs in {f['waves']} monthly waves from {f['first_wave']} to {f['last_wave']}, "
            f"starting with a low risk pilot. Waves were built to keep chatty dependencies together: "
            f"cross-wave traffic is "
            f"{f['cut_weight_optimized']:,.0f} weight units against {f['cut_weight_business_unit']:,.0f} for a plan by "
            f"business unit, {f['cut_reduction_vs_business_unit_pct']}% less. The shared claims database cuts "
            f"over in wave {f['shared_db_wave']} with replication running before it.",
            f"One time migration cost is {_usd(f['one_time_usd'])}. After the program, run cost is "
            f"{_usd(f['steady_state_annual_savings_usd'])} a year lower than staying. Five year NPV of the change is "
            f"{_usd(f['npv_usd'])}. {be}",
            f"The register holds {f['risks']} risks, {f['high_risks']} of them high. The largest: {risks}.",
        ]
    )


def unsupported_numbers(text: str, facts: dict[str, Any]) -> list[str]:
    """Numbers in the text that do not appear anywhere in the facts (after removing commas and $ and %)."""
    blob = json.dumps(facts)
    known = set(re.findall(r"\d+(?:\.\d+)?", blob))
    for x in list(known):
        try:
            v = float(x)
        except ValueError:
            continue
        known.add(f"{v / 1e6:.1f}")  # $3.4M style
        known.add(str(round(v)))
    out = []
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        k = n.replace(",", "")
        if k not in known and k.rstrip("0").rstrip(".") not in known:
            out.append(n)
    return out


def claude_summary(facts: dict[str, Any], client=None, model: str = MODEL) -> dict[str, Any]:
    if client is None:
        import anthropic  # lazy: optional extra

        client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=900,
        system=SYSTEM,
        messages=[{"role": "user", "content": "Facts:\n" + json.dumps(facts, indent=2)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    bad = unsupported_numbers(text, facts)
    return {
        "provider": "claude",
        "model": model,
        "text": text,
        "unsupported_numbers": bad,
        "grounded": not bad,
        "usage": {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
    }


def summarize(facts: dict[str, Any], provider: str = "offline", client=None) -> dict[str, Any]:
    if provider == "claude":
        return claude_summary(facts, client=client)
    text = offline_summary(facts)
    return {
        "provider": "offline",
        "text": text,
        "unsupported_numbers": unsupported_numbers(text, facts),
        "grounded": True,
    }
