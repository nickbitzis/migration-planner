from __future__ import annotations

from datetime import date

import pytest

from migplan.discovery import discover
from migplan.models import Application, Estate, Flow, Server, Team
from migplan.plan import Planner
from migplan.synth import generate


@pytest.fixture(scope="session")
def estate():
    return generate()


@pytest.fixture(scope="session")
def disc(estate):
    return discover(estate)


@pytest.fixture(scope="session")
def planner(estate):
    return Planner(estate)


def make_app(app_id: str, **kw) -> Application:
    base = dict(
        id=app_id,
        name=f"App {app_id}",
        business_unit="Claims",
        kind="standard",
        criticality=3,
        owner_team="team-a",
        tech_stack="Java",
        os="RHEL 8",
        db_engine="none",
        cots=False,
        vendor_product="",
        saas_equivalent=False,
        data_gb=10,
        latency_sensitive=False,
        compliance=[],
        freeze_months=[],
        monthly_users=500,
        years_since_change=1.0,
        deploys_per_year=10,
        business_value=3,
        documented_deps=[],
        hardcoded_ips=[],
    )
    base.update(kw)
    return Application(**base)


def make_server(sid: str, app_id: str | None, ip: str, role: str = "app", **kw) -> Server:
    base = dict(
        id=sid,
        hostname=sid.lower(),
        ip=ip,
        app_id=app_id,
        role=role,
        env="prod",
        os="RHEL 8",
        cores=8,
        ram_gb=32,
        cpu_p95=0.3,
        mem_p95=0.5,
        storage_gb=100,
        physical=False,
        hw_age_years=2,
    )
    base.update(kw)
    return Server(**base)


def tiny_estate(apps: list[Application], servers: list[Server], flows: list[Flow], days: int = 10) -> Estate:
    for s in servers:
        if s.app_id:
            next(a for a in apps if a.id == s.app_id).server_ids.append(s.id)
    return Estate(
        company="Test Co",
        observation_days=days,
        plan_start=date(2027, 1, 1),
        apps={a.id: a for a in apps},
        servers={s.id: s for s in servers},
        flows=flows,
        teams={"team-a": Team("team-a", 2, 2, 3), "team-b": Team("team-b", 2, 2, 3)},
    )
