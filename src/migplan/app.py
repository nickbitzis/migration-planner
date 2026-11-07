"""FastAPI service: inventory, dependency graph, 6R classification and overrides, waves, TCO, risks, exports."""

from __future__ import annotations

import os
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .classify import STRATEGIES, RuleError
from .export import plan_markdown, waves_csv
from .logs import get_logger, log_event
from .metrics import Metrics
from .plan import Planner
from .summary import summarize

STATIC = Path(__file__).parent / "static"


class OverrideRequest(BaseModel):
    strategy: Literal["retain", "retire", "repurchase", "refactor", "replatform", "rehost"]
    by: str = Field(..., min_length=1, max_length=120)
    reason: str = Field(..., min_length=1, max_length=500)


def create_app(planner: Planner | None = None, claude_client=None) -> FastAPI:
    logger = get_logger()
    if planner is None:
        planner = Planner(overrides_path=os.environ.get("MIGPLAN_OVERRIDES"))
    log_event(
        logger,
        "planner_ready",
        apps=len(planner.estate.apps),
        servers=len(planner.estate.servers),
        flows=len(planner.estate.flows),
        startup_seconds=planner.startup_seconds,
    )
    metrics = Metrics()
    app = FastAPI(title="migration-planner", version="1.0.0")
    app.state.planner = planner

    @app.middleware("http")
    async def observe(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        response = await call_next(request)
        dt = time.perf_counter() - t0
        route = request.scope.get("route")
        path = route.path if route is not None else "unmatched"
        metrics.observe(path, response.status_code, dt)
        response.headers["x-request-id"] = rid
        if path not in ("/healthz", "/metrics"):
            log_event(
                logger,
                "request",
                request_id=rid,
                method=request.method,
                route=path,
                status=response.status_code,
                ms=round(dt * 1000, 1),
            )
        return response

    def _app(app_id: str):
        if app_id not in planner.estate.apps:
            raise HTTPException(404, f"no app {app_id}")
        return app_id

    @app.get("/healthz")
    def healthz():
        return {
            "status": "ok",
            "apps": len(planner.estate.apps),
            "servers": len(planner.estate.servers),
            "waves": len(planner.plan.waves),
            "unscheduled": planner.plan.metrics["unscheduled"],
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    def prom():
        mix = Counter(c.strategy for c in planner.classes.values())
        opt = {r["method"]: r for r in planner.comparison}
        gauges = {
            "migplan_apps": ("Applications by 6R strategy", [({"strategy": s}, mix.get(s, 0)) for s in STRATEGIES]),
            "migplan_dependencies": (
                "Discovered dependencies",
                [
                    ({"kind": "observed"}, len(planner.discovery.edges)),
                    ({"kind": "undocumented"}, len(planner.discovery.undocumented)),
                ],
            ),
            "migplan_cross_wave_weight": (
                "Cross-wave dependency weight by planner",
                [({"method": m}, r["total_cut_weight"]) for m, r in opt.items()],
            ),
            "migplan_risks": ("Risks in the register", [({}, len(planner.risks))]),
            "migplan_npv_usd": ("Five year NPV of migrating", [({}, planner.tco["npv"])]),
            "migplan_overrides": (
                "Active 6R overrides",
                [({}, sum(1 for c in planner.classes.values() if c.override))],
            ),
        }
        return metrics.render(gauges)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/summary-stats")
    def stats():
        return planner.facts()

    @app.get("/api/inventory")
    def inventory(
        business_unit: str | None = None, strategy: str | None = None, q: str | None = Query(None, max_length=80)
    ):
        rows = planner.portfolio()
        if business_unit:
            rows = [r for r in rows if r["business_unit"] == business_unit]
        if strategy:
            rows = [r for r in rows if r["strategy"] == strategy]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["name"].lower() or ql in r["id"].lower()]
        return {"count": len(rows), "apps": rows}

    @app.get("/api/inventory/{app_id}")
    def inventory_app(app_id: str):
        return planner.app_detail(_app(app_id))

    @app.get("/api/graph")
    def graph():
        return planner.graph()

    @app.get("/api/classification")
    def classification():
        return {
            "strategies": list(STRATEGIES),
            "rules": [{"id": r["id"], "reason": r["reason"]} for r in planner.rules.rules],
            "apps": [planner.classes[a].to_dict() for a in sorted(planner.classes)],
        }

    @app.get("/api/overrides")
    def list_overrides():
        return [c.override.__dict__ for c in planner.classes.values() if c.override]

    @app.put("/api/overrides/{app_id}")
    def put_override(app_id: str, body: OverrideRequest):
        _app(app_id)
        try:
            o = planner.set_override(app_id, body.strategy, body.by, body.reason)
        except RuleError as exc:
            metrics.event("override", "rejected")
            raise HTTPException(422, str(exc)) from exc
        metrics.event("override", "set")
        log_event(logger, "override_set", app_id=app_id, strategy=o.strategy, by=o.by)
        return {
            "override": o.__dict__,
            "classification": planner.classes[app_id].to_dict(),
            "wave": planner.wave_of(app_id),
        }

    @app.delete("/api/overrides/{app_id}")
    def delete_override(app_id: str):
        _app(app_id)
        if not planner.clear_override(app_id):
            raise HTTPException(404, f"no runtime override for {app_id}")
        metrics.event("override", "cleared")
        return {"classification": planner.classes[app_id].to_dict()}

    @app.get("/api/waves")
    def waves():
        return planner.waves()

    @app.get("/api/tco")
    def tco():
        return planner.tco

    @app.get("/api/risks")
    def risks(category: str | None = None, min_score: int = 0):
        rows = [r.to_dict() for r in planner.risks if (not category or r.category == category) and r.score >= min_score]
        return {"count": len(rows), "risks": rows}

    @app.get("/api/summary")
    def summary(provider: Literal["offline", "claude"] = "offline"):
        if provider == "claude" and claude_client is None and not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(400, "Claude provider needs ANTHROPIC_API_KEY; the offline provider needs nothing")
        out = summarize(planner.facts(), provider, client=claude_client)
        metrics.event("summary", provider)
        return out

    @app.get("/api/export/waves.csv", response_class=PlainTextResponse)
    def export_csv():
        return PlainTextResponse(
            waves_csv(planner), media_type="text/csv", headers={"content-disposition": "attachment; filename=waves.csv"}
        )

    @app.get("/api/export/plan.md", response_class=PlainTextResponse)
    def export_md():
        return PlainTextResponse(
            plan_markdown(planner),
            media_type="text/markdown",
            headers={"content-disposition": "attachment; filename=migration-plan.md"},
        )

    return app
