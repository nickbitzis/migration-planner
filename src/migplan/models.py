"""Domain model: applications, servers, network flows, and the estate that holds them."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

# End of extended support dates used to flag end-of-life platforms. Dates are approximate public vendor dates.
OS_EOL: dict[str, date] = {
    "Windows Server 2008 R2": date(2020, 1, 14),
    "Windows Server 2012 R2": date(2023, 10, 10),
    "Windows Server 2016": date(2027, 1, 12),
    "Windows Server 2019": date(2029, 1, 9),
    "Windows Server 2022": date(2031, 10, 14),
    "RHEL 6": date(2024, 6, 30),
    "RHEL 7": date(2024, 6, 30),
    "RHEL 8": date(2029, 5, 31),
    "RHEL 9": date(2032, 5, 31),
    "Solaris 10": date(2024, 1, 31),
    "AIX 7.1": date(2023, 4, 30),
    "z/OS 2.5": date(2028, 9, 30),
}

DB_COMMERCIAL = {
    "Oracle 11g",
    "Oracle 12c",
    "Oracle 19c",
    "SQL Server 2008",
    "SQL Server 2014",
    "SQL Server 2019",
    "DB2 z/OS",
}


@dataclass
class Team:
    name: str
    cloud_skill: int  # 0 none, 1 basic, 2 working, 3 strong
    container_skill: int
    capacity_per_wave: int  # apps the team can migrate in one wave
    unavailable_waves: list[int] = field(default_factory=list)


@dataclass
class Server:
    id: str
    hostname: str
    ip: str
    app_id: str | None  # None for shared infrastructure (monitoring, backup, directory)
    role: str  # web, app, db, batch, mainframe, monitoring, backup, directory, scanner, patch
    env: str  # prod or nonprod
    os: str
    cores: int
    ram_gb: int
    cpu_p95: float  # 0..1 over the observation window
    mem_p95: float
    storage_gb: int
    physical: bool
    hw_age_years: int


@dataclass
class Flow:
    """One aggregated flow record over the observation window (src, dst, port)."""

    src_ip: str
    dst_ip: str
    port: int
    protocol: str
    connections: int
    bytes: int


@dataclass
class Application:
    id: str
    name: str
    business_unit: str
    kind: str  # standard, shared_database, mainframe
    criticality: int  # 1 mission critical .. 4 administrative
    owner_team: str
    tech_stack: str
    os: str
    db_engine: str
    cots: bool
    vendor_product: str
    saas_equivalent: bool
    data_gb: int
    latency_sensitive: bool
    compliance: list[str]
    freeze_months: list[int]  # calendar months 1..12 when changes are not allowed
    monthly_users: int
    years_since_change: float
    deploys_per_year: int
    business_value: int  # 1..5
    documented_deps: list[str]
    hardcoded_ips: list[str]  # IP literals found by a config scan
    duplicate_of: str | None = None  # another app that already does the same job
    server_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Estate:
    company: str
    observation_days: int
    plan_start: date
    apps: dict[str, Application]
    servers: dict[str, Server]
    flows: list[Flow]
    teams: dict[str, Team]
    truth_deps: set[tuple[str, str]] = field(default_factory=set)  # generator ground truth, used only by tests

    def servers_of(self, app_id: str) -> list[Server]:
        return [self.servers[s] for s in self.apps[app_id].server_ids]

    def ip_index(self) -> dict[str, Server]:
        return {s.ip: s for s in self.servers.values()}


def is_eol(os_name: str, on: date) -> bool:
    d = OS_EOL.get(os_name)
    return d is not None and d <= on
