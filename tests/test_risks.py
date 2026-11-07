from collections import Counter


def test_register_covers_the_expected_categories(planner):
    cats = Counter(r.category for r in planner.risks)
    for c in (
        "latency",
        "shared database",
        "mainframe",
        "discovery",
        "configuration",
        "compliance",
        "skills",
        "retirement",
    ):
        assert cats[c] >= 1, c


def test_ids_sorted_by_score_and_scores_in_range(planner):
    scores = [r.score for r in planner.risks]
    assert scores == sorted(scores, reverse=True)
    assert [r.id for r in planner.risks][:3] == ["R-001", "R-002", "R-003"]
    for r in planner.risks:
        assert 1 <= r.likelihood <= 5 and 1 <= r.impact <= 5 and r.score == r.likelihood * r.impact
        assert r.mitigation and r.owner


def test_latency_risks_are_real_splits(planner):
    for r in [r for r in planner.risks if r.category == "latency"]:
        a, b = r.apps
        assert planner.wave_of(a) != planner.wave_of(b)
        assert planner.estate.apps[a].latency_sensitive or planner.estate.apps[b].latency_sensitive


def test_shared_database_risk_is_top_and_counts_consumers(planner):
    top = planner.risks[0]
    assert top.category == "shared database" and "Claims Data Hub" in top.title and len(top.apps) >= 20


def test_unknown_endpoints_and_hardcoded_ips_are_flagged(planner):
    titles = " ".join(r.title for r in planner.risks)
    assert "10.88.14.21" in titles and "10.88.14.40" in titles
    hard = [r for r in planner.risks if r.category == "configuration"]
    assert hard and all(planner.estate.apps[r.apps[0]].hardcoded_ips for r in hard)


def test_retirement_risk_when_something_still_calls_a_retired_app(planner):
    for r in [r for r in planner.risks if r.category == "retirement"]:
        caller, retired = r.apps if planner.classes[r.apps[1]].strategy == "retire" else r.apps[::-1]
        assert planner.classes[retired].strategy == "retire"
        assert (caller, retired) in planner.discovery.edges
