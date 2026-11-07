"""Dependency discovery: aggregate server flows into an application graph and diff it against the CMDB.

Pipeline per flow record:
1. Resolve both IPs to servers. An IP missing from the inventory is an "unknown endpoint", reported separately.
2. Drop noise: flows touching shared infrastructure (monitoring, backup, directory, patching, scanners), flows on
   noise ports (SNMP, node exporter, NDMP, LDAP, DNS, NTP, WSUS), and flows below both the connection and byte floor.
   The floor is an OR on purpose: a nightly mainframe batch transfer has 14 connections in two weeks but gigabytes.
3. Drop flows between servers of the same application (tier to tier traffic is not a migration dependency).
4. Aggregate the rest to (consumer app, provider app) and weight each edge by volume and chattiness.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .models import Estate

INFRA_ROLES = frozenset({"monitoring", "backup", "directory", "patch", "scanner"})
NOISE_PORTS = frozenset({161, 9100, 5666, 10000, 9392, 389, 636, 88, 53, 123, 8530})


@dataclass
class DiscoveryConfig:
    noise_ports: frozenset[int] = NOISE_PORTS
    infra_roles: frozenset[str] = INFRA_ROLES
    min_connections: int = 10  # over the whole observation window
    min_bytes: int = 50_000_000
    # weight = GB per day + chattiness_per_10k * (connections per day / 10,000)
    # Chatty links hurt more than their bytes suggest: every round trip pays WAN latency once the two ends split.
    chattiness_per_10k: float = 1.0


@dataclass
class Edge:
    src: str
    dst: str
    bytes: int = 0
    connections: int = 0
    flows: int = 0
    ports: set[int] = field(default_factory=set)
    gb_per_day: float = 0.0
    conns_per_day: float = 0.0
    weight: float = 0.0

    def to_dict(self) -> dict:
        return {
            "src": self.src,
            "dst": self.dst,
            "bytes": self.bytes,
            "connections": self.connections,
            "flows": self.flows,
            "ports": sorted(self.ports),
            "gb_per_day": round(self.gb_per_day, 3),
            "conns_per_day": round(self.conns_per_day, 1),
            "weight": round(self.weight, 3),
        }


@dataclass
class Discovery:
    edges: dict[tuple[str, str], Edge]
    noise: dict[str, dict[str, int]]  # reason -> {flows, bytes}
    unknown_endpoints: list[dict]
    undocumented: list[dict]
    stale_documented: list[dict]
    confirmed: int
    kept_flows: int
    total_flows: int

    def undirected(self) -> dict[tuple[str, str], float]:
        """Symmetric weights keyed (a, b) with a < b, used by wave planning."""
        out: dict[tuple[str, str], float] = defaultdict(float)
        for (a, b), e in self.edges.items():
            out[(a, b) if a < b else (b, a)] += e.weight
        return dict(out)

    def neighbors(self, app_id: str) -> set[str]:
        return {b for (a, b) in self.edges if a == app_id} | {a for (a, b) in self.edges if b == app_id}


def discover(estate: Estate, cfg: DiscoveryConfig | None = None) -> Discovery:
    cfg = cfg or DiscoveryConfig()
    ipx = estate.ip_index()
    days = estate.observation_days
    noise: dict[str, dict[str, int]] = defaultdict(lambda: {"flows": 0, "bytes": 0})
    unknown: dict[str, dict] = {}
    edges: dict[tuple[str, str], Edge] = {}
    kept = 0
    for f in estate.flows:
        src, dst = ipx.get(f.src_ip), ipx.get(f.dst_ip)
        reason = None
        if src is None or dst is None:
            known = src or dst
            if known is not None and known.app_id and known.role not in cfg.infra_roles:
                ip = f.dst_ip if dst is None else f.src_ip
                u = unknown.setdefault(ip, {"ip": ip, "apps": set(), "ports": set(), "bytes": 0, "connections": 0})
                u["apps"].add(known.app_id)
                u["ports"].add(f.port)
                u["bytes"] += f.bytes
                u["connections"] += f.connections
            reason = "unknown_endpoint"
        elif src.role in cfg.infra_roles or dst.role in cfg.infra_roles:
            reason = "infrastructure"
        elif f.port in cfg.noise_ports:
            reason = "noise_port"
        elif f.connections < cfg.min_connections and f.bytes < cfg.min_bytes:
            reason = "below_threshold"
        elif src.app_id == dst.app_id:
            reason = "intra_app"
        if reason:
            noise[reason]["flows"] += 1
            noise[reason]["bytes"] += f.bytes
            continue
        kept += 1
        key = (src.app_id, dst.app_id)
        e = edges.get(key) or edges.setdefault(key, Edge(*key))
        e.bytes += f.bytes
        e.connections += f.connections
        e.flows += 1
        e.ports.add(f.port)
    for e in edges.values():
        e.gb_per_day = e.bytes / 1e9 / days
        e.conns_per_day = e.connections / days
        e.weight = e.gb_per_day + cfg.chattiness_per_10k * e.conns_per_day / 10_000

    observed = set(edges)
    documented = {(a.id, d) for a in estate.apps.values() for d in a.documented_deps}
    obs_undirected = observed | {(b, a) for a, b in observed}
    undocumented = [
        dict(edges[k].to_dict(), src_name=estate.apps[k[0]].name, dst_name=estate.apps[k[1]].name)
        for k in sorted(observed - documented)
    ]
    undocumented.sort(key=lambda d: -d["weight"])
    stale = [
        {"src": a, "dst": b, "src_name": estate.apps[a].name, "dst_name": estate.apps[b].name}
        for a, b in sorted(documented - obs_undirected)
    ]
    unknown_list = [dict(u, apps=sorted(u["apps"]), ports=sorted(u["ports"])) for u in unknown.values()]
    unknown_list.sort(key=lambda u: -u["bytes"])
    return Discovery(
        edges=edges,
        noise=dict(noise),
        unknown_endpoints=unknown_list,
        undocumented=undocumented,
        stale_documented=stale,
        confirmed=len(observed & documented),
        kept_flows=kept,
        total_flows=len(estate.flows),
    )


def precision_recall(disc: Discovery, truth: set[tuple[str, str]]) -> dict[str, float]:
    """Score discovery against generator ground truth (only possible on synthetic data)."""
    found = set(disc.edges)
    tp = len(found & truth)
    return {
        "precision": tp / len(found) if found else 0.0,
        "recall": tp / len(truth) if truth else 0.0,
        "found": len(found),
        "truth": len(truth),
    }
