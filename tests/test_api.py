import csv
import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from migplan.app import create_app
from migplan.plan import Planner
from migplan.summary import unsupported_numbers


class FakeClaude:
    def __init__(self, text):
        self.text, self.calls = text, []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            usage=SimpleNamespace(input_tokens=900, output_tokens=200),
        )


@pytest.fixture(scope="module")
def client(planner):
    return TestClient(create_app(planner))


def test_healthz_and_request_id(client):
    r = client.get("/healthz", headers={"x-request-id": "abc123"})
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["unscheduled"] == 0
    assert r.headers["x-request-id"] == "abc123"


def test_metrics_prometheus_format(client):
    client.get("/api/waves")
    body = client.get("/metrics").text
    assert 'migplan_requests_total{route="/api/waves",status="200"}' in body
    assert 'migplan_apps{strategy="retain"}' in body and "migplan_cross_wave_weight" in body


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "migration-planner" in r.text


def test_inventory_filters_and_detail(client):
    all_ = client.get("/api/inventory").json()
    assert all_["count"] == 250
    rep = client.get("/api/inventory", params={"strategy": "repurchase"}).json()
    assert rep["count"] > 0 and all(a["strategy"] == "repurchase" for a in rep["apps"])
    assert client.get("/api/inventory", params={"q": "claims data"}).json()["apps"][0]["id"] == "APP-249"
    d = client.get("/api/inventory/APP-249").json()
    assert d["app"]["kind"] == "shared_database" and len(d["neighbors"]) == 30 and d["servers"]
    assert client.get("/api/inventory/APP-999").status_code == 404


def test_graph_endpoint(client):
    g = client.get("/api/graph").json()
    assert len(g["nodes"]) == 250 and len(g["edges"]) == 340
    assert len(g["undocumented"]) == sum(1 for e in g["edges"] if not e["documented"])
    assert g["accuracy_vs_truth"]["recall"] == 1.0


def test_classification_waves_tco_risks(client):
    c = client.get("/api/classification").json()
    assert len(c["apps"]) == 250 and all(a["reasons"] for a in c["apps"])
    w = client.get("/api/waves").json()
    assert len(w["waves"]) == 14 and {r["method"] for r in w["comparison"]} == {
        "optimized",
        "alphabetical",
        "business_unit",
    }
    assert w["shared_database"]["wave"] == w["metrics"]["hub_wave"]
    t = client.get("/api/tco").json()
    assert t["npv"] > 0 and "assumptions" in t
    r = client.get("/api/risks", params={"min_score": 15}).json()
    assert r["count"] > 0 and all(x["score"] >= 15 for x in r["risks"])
    assert client.get("/api/risks", params={"category": "mainframe"}).json()["count"] == 1


def test_exports(client):
    r = client.get("/api/export/waves.csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert r.headers["content-type"].startswith("text/csv")
    assert {row["wave"] for row in rows} == {str(i) for i in range(1, 15)}
    assert any(row["app_id"] == "APP-249" for row in rows)
    md = client.get("/api/export/plan.md").text
    assert md.startswith("# Migration plan: Kestrel Ridge Mutual") and "## Wave comparison" in md
    assert "## Risk register" in md and "### Assumptions" in md


def test_override_end_to_end(estate, tmp_path):
    path = tmp_path / "overrides.json"
    pl = Planner(estate, overrides_path=path)
    c = TestClient(create_app(pl))
    target = next(a for a in sorted(pl.plan.where) if pl.classes[a].strategy == "rehost")
    before = c.get("/api/waves").json()["metrics"]["scheduled"]
    r = c.put(f"/api/overrides/{target}", json={"strategy": "retire", "by": "App owner", "reason": "Replaced"})
    assert r.status_code == 200 and r.json()["classification"]["strategy"] == "retire"
    assert r.json()["classification"]["computed"] == "rehost" and r.json()["wave"] is None
    assert c.get("/api/waves").json()["metrics"]["scheduled"] == before - 1
    assert any(o["app_id"] == target and o["by"] == "App owner" for o in c.get("/api/overrides").json())
    saved = json.loads(path.read_text())
    assert saved[0]["app_id"] == target and saved[0]["reason"] == "Replaced"
    assert Planner(estate, overrides_path=path).classes[target].strategy == "retire"  # survives restart
    assert c.delete(f"/api/overrides/{target}").status_code == 200
    assert pl.classes[target].strategy == "rehost"
    assert c.delete(f"/api/overrides/{target}").status_code == 404


def test_override_validation(client):
    assert client.put("/api/overrides/APP-001", json={"strategy": "retire", "by": "", "reason": "x"}).status_code == 422
    assert client.put("/api/overrides/APP-001", json={"strategy": "lift", "by": "a", "reason": "x"}).status_code == 422
    assert (
        client.put("/api/overrides/APP-999", json={"strategy": "retire", "by": "a", "reason": "x"}).status_code == 404
    )


def test_offline_summary_uses_only_facts(client):
    s = client.get("/api/summary").json()
    assert s["provider"] == "offline" and s["unsupported_numbers"] == []
    assert "Kestrel Ridge Mutual" in s["text"]


def test_claude_summary_with_fake_client_and_grounding_check(planner):
    facts = planner.facts()
    good = FakeClaude(f"The plan moves {facts['apps']} apps in {facts['waves']} waves.")
    c = TestClient(create_app(planner, claude_client=good))
    s = c.get("/api/summary", params={"provider": "claude"}).json()
    assert s["grounded"] and s["usage"]["output_tokens"] == 200
    sent = good.calls[0]
    assert sent["model"] == "claude-opus-5-5" and json.loads(sent["messages"][0]["content"].split("\n", 1)[1]) == facts
    bad = FakeClaude("Savings will reach 47 million dollars.")
    s2 = TestClient(create_app(planner, claude_client=bad)).get("/api/summary", params={"provider": "claude"}).json()
    assert not s2["grounded"] and "47" in s2["unsupported_numbers"]


def test_claude_provider_without_key_is_a_clear_400(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert client.get("/api/summary", params={"provider": "claude"}).status_code == 400


def test_unsupported_numbers_accepts_millions_formatting():
    assert unsupported_numbers("NPV is $3.4M over 60 months", {"npv": 3401080, "months": 60}) == []
    assert unsupported_numbers("about 12 risks", {"risks": 13}) == ["12"]
