from migplan.discovery import DiscoveryConfig, discover, precision_recall
from migplan.models import Flow

from .conftest import make_app, make_server, tiny_estate


def _estate(flows, a_deps=()):
    apps = [make_app("A", documented_deps=list(a_deps)), make_app("B"), make_app("C"), make_app("D")]
    servers = [
        make_server("S1", "A", "10.0.0.1"),
        make_server("S2", "A", "10.0.0.2"),
        make_server("S3", "B", "10.0.0.3"),
        make_server("S4", "B", "10.0.0.4", role="db"),
        make_server("S5", "C", "10.0.0.5"),
        make_server("S6", "D", "10.0.0.6"),
        make_server("M1", None, "10.9.0.1", role="monitoring"),
        make_server("K1", None, "10.9.0.2", role="backup"),
    ]
    return tiny_estate(apps, servers, flows)


GB = 1_000_000_000


def test_aggregates_server_flows_to_one_app_edge():
    e = _estate(
        [
            Flow("10.0.0.1", "10.0.0.3", 8443, "tcp", 1000, 2 * GB),
            Flow("10.0.0.2", "10.0.0.4", 1521, "tcp", 3000, 3 * GB),
        ]
    )
    d = discover(e)
    assert list(d.edges) == [("A", "B")]
    edge = d.edges[("A", "B")]
    assert edge.bytes == 5 * GB and edge.connections == 4000 and edge.flows == 2 and edge.ports == {8443, 1521}


def test_edge_weight_combines_volume_and_chattiness():
    e = _estate([Flow("10.0.0.1", "10.0.0.3", 443, "tcp", 200_000, 10 * GB)])  # 10 days
    edge = discover(e).edges[("A", "B")]
    assert abs(edge.gb_per_day - 1.0) < 1e-9
    assert abs(edge.conns_per_day - 20_000) < 1e-9
    assert abs(edge.weight - (1.0 + 2.0)) < 1e-9
    edge2 = discover(e, DiscoveryConfig(chattiness_per_10k=0)).edges[("A", "B")]
    assert abs(edge2.weight - 1.0) < 1e-9


def test_infrastructure_traffic_is_dropped():
    e = _estate(
        [Flow("10.9.0.1", "10.0.0.1", 9100, "tcp", 9999, GB), Flow("10.9.0.2", "10.0.0.3", 10000, "tcp", 10, 500 * GB)]
    )
    d = discover(e)
    assert d.edges == {}
    assert d.noise["infrastructure"]["flows"] == 2


def test_noise_ports_between_app_servers_are_dropped():
    e = _estate([Flow("10.0.0.1", "10.0.0.5", 161, "udp", 5000, GB), Flow("10.0.0.1", "10.0.0.5", 53, "udp", 5000, GB)])
    d = discover(e)
    assert d.edges == {} and d.noise["noise_port"]["flows"] == 2


def test_threshold_drops_tiny_flows_but_keeps_low_count_high_volume_batch():
    e = _estate(
        [
            Flow("10.0.0.1", "10.0.0.5", 22, "tcp", 2, 40_000),  # stray ssh
            Flow("10.0.0.1", "10.0.0.6", 1364, "tcp", 7, 20 * GB),
        ]
    )  # nightly batch file
    d = discover(e)
    assert ("A", "C") not in d.edges and ("A", "D") in d.edges
    assert d.noise["below_threshold"]["flows"] == 1


def test_intra_app_traffic_is_not_a_dependency():
    e = _estate([Flow("10.0.0.3", "10.0.0.4", 1521, "tcp", 10_000, 9 * GB)])
    d = discover(e)
    assert d.edges == {} and d.noise["intra_app"]["flows"] == 1


def test_unknown_endpoint_reported_with_calling_apps():
    e = _estate(
        [Flow("10.0.0.1", "10.77.0.9", 1433, "tcp", 500, GB), Flow("10.0.0.3", "10.77.0.9", 1433, "tcp", 50, GB)]
    )
    d = discover(e)
    assert d.edges == {}
    assert d.unknown_endpoints == [
        {"ip": "10.77.0.9", "apps": ["A", "B"], "ports": [1433], "bytes": 2 * GB, "connections": 550}
    ]


def test_undocumented_and_stale_dependencies():
    flows = [Flow("10.0.0.1", "10.0.0.3", 443, "tcp", 1000, GB), Flow("10.0.0.1", "10.0.0.5", 443, "tcp", 1000, GB)]
    e = _estate(flows, a_deps=["B", "D"])
    d = discover(e)
    assert [(u["src"], u["dst"]) for u in d.undocumented] == [("A", "C")]
    assert [(s["src"], s["dst"]) for s in d.stale_documented] == [("A", "D")]
    assert d.confirmed == 1


def test_documented_in_reverse_direction_is_not_stale():
    e = _estate([Flow("10.0.0.3", "10.0.0.1", 443, "tcp", 1000, GB)], a_deps=["B"])
    d = discover(e)
    assert d.stale_documented == []
    assert [(u["src"], u["dst"]) for u in d.undocumented] == [("B", "A")]


def test_sample_estate_discovery_matches_ground_truth(estate, disc):
    pr = precision_recall(disc, estate.truth_deps)
    assert pr["precision"] == 1.0 and pr["recall"] == 1.0
    documented = {(a.id, d) for a in estate.apps.values() for d in a.documented_deps}
    assert len(disc.undocumented) == len(estate.truth_deps - documented)
    assert len(disc.undocumented) >= 60
    assert len(disc.stale_documented) == 15


def test_sample_estate_noise_is_most_of_the_flows(disc):
    assert disc.noise["infrastructure"]["flows"] > disc.kept_flows * 5
    assert all(a and b for a, b in disc.edges)


def test_sample_shared_database_and_mainframe_traps(estate, disc):
    hub = next(a for a in estate.apps.values() if a.kind == "shared_database")
    mf = next(a for a in estate.apps.values() if a.kind == "mainframe")
    consumers = {a for (a, b) in disc.edges if b == hub.id}
    assert len(consumers) == 30
    assert sum(1 for u in disc.undocumented if u["dst"] == hub.id) == 8
    batch = [e for (a, b), e in disc.edges.items() if b == mf.id and 1364 in e.ports]
    assert len(batch) >= 10  # one batch app was later given online MQ calls instead
    assert all(e.connections < 100 for e in batch)
    assert {u["ip"] for u in disc.unknown_endpoints} == {"10.88.14.21", "10.88.14.40"}


def test_undirected_weights_are_symmetric_sums():
    e = _estate(
        [Flow("10.0.0.1", "10.0.0.3", 443, "tcp", 0, 10 * GB), Flow("10.0.0.3", "10.0.0.1", 443, "tcp", 0, 20 * GB)]
    )
    und = discover(e, DiscoveryConfig(min_connections=0)).undirected()
    assert list(und) == [("A", "B")] and abs(und[("A", "B")] - 3.0) < 1e-9
