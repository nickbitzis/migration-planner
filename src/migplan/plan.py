"""Orchestration: estate -> discovery -> 6R -> waves -> TCO -> risks, recomputed when an override changes."""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from pathlib import Path

from .classify import Override, Rules, classify, features
from .discovery import Discovery, DiscoveryConfig, discover, precision_recall
from .models import Estate, is_eol
from .risks import generate_risks
from .synth import SynthConfig, generate
from .tco import TcoAssumptions, compute_tco
from .waves import LABELS, WaveConfig, build_problem, compare


class Planner:
    def __init__(
        self,
        estate: Estate | None = None,
        rules: Rules | None = None,
        wave_cfg: WaveConfig | None = None,
        tco: TcoAssumptions | None = None,
        disc_cfg: DiscoveryConfig | None = None,
        overrides_path: str | Path | None = None,
    ):
        t0 = time.perf_counter()
        self.estate = estate or generate(SynthConfig())
        self.rules = rules or Rules.load()
        self.wave_cfg = wave_cfg or WaveConfig()
        self.tco_assumptions = tco or TcoAssumptions(plan_start=self.estate.plan_start)
        self.disc_cfg = disc_cfg or DiscoveryConfig()
        self.overrides_path = Path(overrides_path) if overrides_path else None
        self.overrides: dict[str, Override] = {}
        self.lock = threading.Lock()
        if self.overrides_path and self.overrides_path.exists():
            for o in json.loads(self.overrides_path.read_text()):
                self.overrides[o["app_id"]] = Override(**o)
        self.discovery: Discovery = discover(self.estate, self.disc_cfg)
        self.recompute()
        self.startup_seconds = round(time.perf_counter() - t0, 3)

    # ---- pipeline ----
    def recompute(self) -> None:
        e, d = self.estate, self.discovery
        self.classes = classify(e, d, self.rules, self.overrides)
        self.problem = build_problem(e, d, self.classes, self.wave_cfg)
        cmp_ = compare(self.problem)
        self.plans = cmp_["plans"]
        self.comparison = cmp_["rows"]
        self.plan = self.plans["optimized"]
        hub = (self.problem.hub, self.plan.hub_wave) if self.problem.hub and self.plan.hub_wave else None
        gb = {k: v.gb_per_day for k, v in d.edges.items()}
        self.tco = compute_tco(e, self.classes, self.plan.where, self.tco_assumptions, hub=hub, gb_edges=gb)
        self.risks = generate_risks(e, d, self.classes, self.problem, self.plan)

    def set_override(self, app_id: str, strategy: str, by: str, reason: str) -> Override:
        if app_id not in self.estate.apps:
            raise KeyError(app_id)
        o = Override(app_id=app_id, strategy=strategy, by=by, reason=reason)
        with self.lock:
            self.overrides[app_id] = o
            self._save()
            self.recompute()
        return o

    def clear_override(self, app_id: str) -> bool:
        with self.lock:
            existed = self.overrides.pop(app_id, None) is not None
            if existed:
                self._save()
                self.recompute()
        return existed

    def _save(self) -> None:
        if self.overrides_path:
            self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
            self.overrides_path.write_text(json.dumps([o.__dict__ for o in self.overrides.values()], indent=2))

    # ---- views ----
    def wave_of(self, app_id: str) -> int | None:
        if app_id == self.problem.hub:
            return self.plan.hub_wave
        return self.plan.where.get(app_id)

    def portfolio(self) -> list[dict]:
        out = []
        for a, app in sorted(self.estate.apps.items()):
            c = self.classes[a]
            out.append(
                {
                    "id": a,
                    "name": app.name,
                    "business_unit": app.business_unit,
                    "owner_team": app.owner_team,
                    "criticality": app.criticality,
                    "tech_stack": app.tech_stack,
                    "os": app.os,
                    "os_eol": is_eol(app.os, self.estate.plan_start),
                    "db_engine": app.db_engine,
                    "compliance": app.compliance,
                    "servers": len(app.server_ids),
                    "monthly_users": app.monthly_users,
                    "strategy": c.strategy,
                    "computed": c.computed,
                    "confidence": c.confidence,
                    "scores": c.scores,
                    "reasons": c.reasons,
                    "main_reason": c.main_reason,
                    "wave": self.wave_of(a),
                    "override": c.override.__dict__ if c.override else None,
                    "kind": app.kind,
                    "latency_sensitive": app.latency_sensitive,
                }
            )
        return out

    def app_detail(self, app_id: str) -> dict:
        app = self.estate.apps[app_id]
        return {
            "app": app.to_dict(),
            "features": features(app_id, self.estate, self.discovery),
            "classification": self.classes[app_id].to_dict(),
            "wave": self.wave_of(app_id),
            "servers": [s.__dict__ for s in self.estate.servers_of(app_id)],
            "neighbors": sorted(self.discovery.neighbors(app_id)),
        }

    def graph(self) -> dict:
        documented = {(a.id, d) for a in self.estate.apps.values() for d in a.documented_deps}
        nodes = [
            {
                "id": a,
                "name": app.name,
                "bu": app.business_unit,
                "strategy": self.classes[a].strategy,
                "wave": self.wave_of(a),
                "kind": app.kind,
            }
            for a, app in sorted(self.estate.apps.items())
        ]
        edges = [dict(e.to_dict(), documented=k in documented) for k, e in sorted(self.discovery.edges.items())]
        d = self.discovery
        return {
            "nodes": nodes,
            "edges": edges,
            "undocumented": d.undocumented,
            "stale_documented": d.stale_documented,
            "unknown_endpoints": d.unknown_endpoints,
            "noise": d.noise,
            "kept_flows": d.kept_flows,
            "total_flows": d.total_flows,
            "confirmed": d.confirmed,
            "accuracy_vs_truth": precision_recall(d, self.estate.truth_deps) if self.estate.truth_deps else None,
        }

    def waves(self) -> dict:
        p = self.problem
        teams = {}
        for w in self.plan.waves:
            for a in w["apps"]:
                teams.setdefault(w["wave"], Counter())[p.team[a]] += 1
        waves = []
        for w in self.plan.waves:
            waves.append(
                dict(w, teams=dict(teams.get(w["wave"], {})), app_names=[self.estate.apps[a].name for a in w["apps"]])
            )
        hub = None
        if p.hub:
            hub = {
                "app_id": p.hub,
                "name": self.estate.apps[p.hub].name,
                "wave": self.plan.hub_wave,
                "consumers": len(p.hub_weights),
                "approach": "Excluded from partitioning. Replication starts in wave 2; the database cuts over in "
                "the wave that minimizes consumer traffic across the WAN, outside its freeze.",
            }
        return {
            "method": self.plan.method,
            "label": LABELS[self.plan.method],
            "waves": waves,
            "metrics": self.plan.metrics,
            "comparison": self.comparison,
            "shared_database": hub,
            "config": self.wave_cfg.__dict__,
            "not_moving": self.not_moving(),
        }

    def not_moving(self) -> dict:
        out = {"retire": [], "retain": []}
        for a, c in self.classes.items():
            if c.strategy in out:
                out[c.strategy].append(a)
        return out

    def facts(self) -> dict:
        """The only input the executive summary is allowed to use."""
        mix = Counter(c.strategy for c in self.classes.values())
        opt = next(r for r in self.comparison if r["method"] == "optimized")
        bu = next(r for r in self.comparison if r["method"] == "business_unit")
        alpha = next(r for r in self.comparison if r["method"] == "alphabetical")
        top = [r.to_dict() for r in self.risks[:5]]
        return {
            "company": self.estate.company,
            "apps": len(self.estate.apps),
            "servers": len(self.estate.servers),
            "strategy_mix": dict(sorted(mix.items())),
            "overrides": len([c for c in self.classes.values() if c.override]),
            "dependencies_discovered": len(self.discovery.edges),
            "undocumented_dependencies": len(self.discovery.undocumented),
            "unknown_endpoints": len(self.discovery.unknown_endpoints),
            "waves": self.wave_cfg.n_waves,
            "first_wave": self.plan.waves[0]["label"],
            "last_wave": self.plan.waves[-1]["label"],
            "shared_db_wave": self.plan.hub_wave,
            "cut_weight_optimized": opt["total_cut_weight"],
            "cut_weight_business_unit": bu["total_cut_weight"],
            "cut_weight_alphabetical": alpha["total_cut_weight"],
            "cut_reduction_vs_business_unit_pct": round(opt["reduction_vs_bu"] * 100, 1),
            "wan_gb_optimized": opt["total_wan_gb"],
            "wan_gb_business_unit": bu["total_wan_gb"],
            "npv_usd": self.tco["npv"],
            "break_even_month": self.tco["break_even_month"],
            "break_even_date": self.tco["break_even_date"],
            "one_time_usd": self.tco["one_time_total"],
            "steady_state_annual_savings_usd": self.tco["steady_state_annual_savings"],
            "risks": len(self.risks),
            "high_risks": sum(1 for r in self.risks if r.score >= 15),
            "top_risks": [{"id": r["id"], "title": r["title"], "score": r["score"]} for r in top],
        }
