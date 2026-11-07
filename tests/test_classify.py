import pytest

from migplan.classify import STRATEGIES, Override, RuleError, Rules, classify, classify_app, evaluate

NEUTRAL = {
    "id": "X",
    "name": "X",
    "business_unit": "Claims",
    "kind": "standard",
    "os": "RHEL 8",
    "platform": "x86",
    "os_eol": False,
    "os_eol_by_plan_end": False,
    "os_eol_date": "",
    "db_engine": "PostgreSQL 13",
    "db_commercial": False,
    "cots": False,
    "vendor_product": "none",
    "saas_equivalent": False,
    "monthly_users": 500,
    "years_since_change": 1.0,
    "deploys_per_year": 10,
    "criticality": 3,
    "business_value": 3,
    "latency_sensitive": False,
    "compliance": [],
    "data_gb": 100,
    "tech_stack": "Java",
    "owner_team": "t",
    "team_cloud_skill": 2,
    "team_container_skill": 1,
    "dependents": 0,
    "dependencies": 0,
    "calls_mainframe_online": False,
    "duplicate": False,
    "duplicate_of_name": "",
    "servers": 2,
    "hardcoded_ips": 0,
}


@pytest.fixture(scope="module")
def rules():
    return Rules.load()


def run(rules, **kw):
    return classify_app(dict(NEUTRAL, **kw), rules)


def fired(c):
    return [r["rule"] for r in c.reasons]


def test_neutral_app_defaults_to_rehost(rules):
    c = run(rules)
    assert c.strategy == "rehost" and fired(c) == ["default"]


@pytest.mark.parametrize(
    "change, rule, winner",
    [
        ({"platform": "mainframe", "os": "z/OS 2.5", "team_cloud_skill": 0}, "retain_mainframe", "retain"),
        ({"duplicate": True, "duplicate_of_name": "Twin", "monthly_users": 12}, "retire_duplicate", "retire"),
        ({"os_eol": True, "os": "RHEL 6", "monthly_users": 20}, "retire_eol_low_use", "retire"),
        ({"years_since_change": 6.0, "monthly_users": 10, "deploys_per_year": 0}, "retire_dormant", "retire"),
        ({"os_eol": True, "monthly_users": 20, "dependents": 4}, "retire_blocked_by_callers", "rehost"),
        ({"cots": True, "saas_equivalent": True, "vendor_product": "PayFlex HR"}, "repurchase_saas", "repurchase"),
        ({"cots": True, "vendor_product": "LedgerWorks"}, "cots_vendor_install", "rehost"),
        ({"platform": "unix", "os": "Solaris 10"}, "unix_cannot_rehost", "replatform"),
        ({"os_eol": True, "os": "Windows Server 2012 R2"}, "eol_os_needs_upgrade", "replatform"),
        ({"os_eol_by_plan_end": True, "os": "Windows Server 2016"}, "os_eol_soon", "replatform"),  # tie, order wins
        ({"db_commercial": True, "db_engine": "Oracle 19c"}, "managed_database", "replatform"),
        ({"kind": "shared_database", "dependents": 30, "monthly_users": 0}, "shared_database", "replatform"),
        ({"business_value": 5, "deploys_per_year": 40, "team_container_skill": 3}, "refactor_high_value", "refactor"),
        (
            {"team_cloud_skill": 0, "business_value": 5, "deploys_per_year": 40, "team_container_skill": 3},
            "refactor_needs_skills",
            "rehost",
        ),
        ({"tech_stack": ".NET Framework", "team_container_skill": 2}, "dotnet_framework_containers", "replatform"),
        ({"calls_mainframe_online": True}, "mainframe_online_latency", "retain"),
        ({"deploys_per_year": 2}, "stable_lift_and_shift", "rehost"),
    ],
)
def test_each_rule_fires_and_moves_the_result(rules, change, rule, winner):
    c = run(rules, **change)
    assert rule in fired(c)
    assert c.strategy == winner
    reason = next(r for r in c.reasons if r["rule"] == rule)
    assert "{" not in reason["text"]


def test_every_rule_in_yaml_is_covered_by_a_test(rules):
    tested = {
        "retain_mainframe",
        "retire_duplicate",
        "retire_eol_low_use",
        "retire_dormant",
        "retire_blocked_by_callers",
        "repurchase_saas",
        "cots_vendor_install",
        "unix_cannot_rehost",
        "eol_os_needs_upgrade",
        "os_eol_soon",
        "managed_database",
        "shared_database",
        "refactor_high_value",
        "refactor_needs_skills",
        "dotnet_framework_containers",
        "mainframe_online_latency",
        "stable_lift_and_shift",
    }
    assert {r["id"] for r in rules.rules} == tested


def test_scores_sum_rule_contributions_and_confidence(rules):
    c = run(rules, cots=True, saas_equivalent=True)
    assert c.scores["repurchase"] == 4.0 and c.scores["rehost"] == 1.0
    assert c.confidence == pytest.approx((4 - 1) / 4, abs=1e-3)


def test_ties_break_in_strategy_order():
    r = Rules.load(
        text="strategies: [retain, retire, repurchase, refactor, replatform, rehost]\n"
        "base: {rehost: 1, retire: 1}\nrules: []\n"
    )
    assert classify_app(dict(NEUTRAL), r).strategy == "retire"


def test_conditions_any_and_not():
    assert evaluate({"any": [{"field": "cots", "eq": True}, {"field": "monthly_users", "gt": 100}]}, NEUTRAL)
    assert not evaluate({"not": {"field": "monthly_users", "gt": 100}}, NEUTRAL)
    assert evaluate({"field": "os", "in": ["RHEL 8", "RHEL 9"]}, NEUTRAL)


@pytest.mark.parametrize(
    "text, msg",
    [
        ("rules: [{id: a, when: {field: nope, eq: 1}, scores: {rehost: 1}, reason: x}]", "unknown field"),
        ("rules: [{id: a, when: {field: cots, eq: true}, scores: {lift: 1}, reason: x}]", "unknown strategies"),
        ("rules: [{id: a, when: {field: cots, eq: true}, reason: x}]", "missing scores"),
        (
            "rules: [{id: a, when: {field: cots, eq: true}, scores: {}, reason: x},"
            " {id: a, when: {field: cots, eq: true}, scores: {}, reason: x}]",
            "duplicate rule id",
        ),
        ("rules: [{id: a, when: {field: cots, approx: true}, scores: {}, reason: x}]", "needs exactly one"),
    ],
)
def test_bad_rules_are_rejected(text, msg):
    with pytest.raises(RuleError, match=msg):
        r = Rules.load(text=text)
        classify_app(dict(NEUTRAL), r)


def test_override_needs_who_and_why():
    with pytest.raises(RuleError):
        Override("APP-001", "retire", by="", reason="x")
    with pytest.raises(RuleError):
        Override("APP-001", "retire", by="arch board", reason=" ")
    with pytest.raises(RuleError):
        Override("APP-001", "lift", by="a", reason="b")


def test_override_changes_final_strategy_and_keeps_computed(estate, disc, rules):
    o = Override("APP-005", "refactor", by="CTO office", reason="Strategic rebuild")
    c = classify(estate, disc, rules, {"APP-005": o})["APP-005"]
    assert c.strategy == "refactor" and c.computed != "refactor"
    d = c.to_dict()
    assert d["overridden"] and d["override"]["by"] == "CTO office" and d["override"]["at"]


def test_config_overrides_from_yaml_are_applied(estate, disc, rules):
    c = classify(estate, disc, rules)["APP-201"]
    assert c.strategy == "retain" and c.override.source == "config" and c.override.by


def test_sample_mix_is_plausible(planner):
    mix = {s: 0 for s in STRATEGIES}
    for c in planner.classes.values():
        mix[c.strategy] += 1
    assert mix["retain"] >= 2 and mix["retire"] >= 15 and mix["repurchase"] >= 15 and mix["refactor"] >= 3
    assert planner.classes["APP-250"].strategy == "retain"
    assert planner.classes["APP-249"].strategy == "replatform"


def test_main_reason_is_the_rule_that_decided(rules):
    c = run(rules, dependents=4, cots=True, saas_equivalent=True, vendor_product="PayFlex HR")
    assert c.strategy == "repurchase" and "SaaS edition" in c.main_reason
    assert run(rules).main_reason == "Rehost is the default and no rule scored higher"
