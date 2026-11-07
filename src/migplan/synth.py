"""Seeded synthetic estate for Kestrel Ridge Mutual, a made-up regional insurer leaving its data center.

The generator builds a ground-truth dependency graph first, then derives what a migration team would actually see:
a CMDB inventory whose documented dependencies are incomplete and partly stale, and two weeks of aggregated network
flows that contain the real dependencies buried in monitoring, backup, directory, and scanner noise.

Traps planted on purpose:
- about a quarter of real dependencies are missing from the inventory and only show up in flows
- one Oracle database ("Claims Data Hub") is shared by 30 applications, several of them undocumented
- a mainframe policy system exchanges nightly batch files with a dozen apps (few connections, many bytes)
- some apps have IP literals in their config files, which break on rehost
- two IPs in the flows belong to servers that are not in the CMDB at all
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .models import Application, Estate, Flow, Server, Team

COMPANY = "Kestrel Ridge Mutual"

# business unit: (app count, freeze months, team names, name nouns)
BUSINESS_UNITS: dict[str, tuple[int, list[int], list[str], list[str]]] = {
    "Personal Lines": (
        48,
        [3],
        ["policy-core", "auto-rating", "home-quote"],
        [
            "Auto Quote",
            "Home Rating",
            "Policy Issuance",
            "Endorsement",
            "Renewal",
            "Telematics",
            "Underwriting Rules",
            "Billing Plan",
            "Coverage Selector",
            "Discount",
        ],
    ),
    "Commercial Lines": (
        34,
        [6],
        ["commercial-uw", "specialty-lines"],
        [
            "Submission",
            "Risk Survey",
            "Workers Comp",
            "Fleet Rating",
            "Bond",
            "Loss Control",
            "Broker Quote",
            "Exposure",
        ],
    ),
    "Claims": (
        44,
        [8, 9, 10],
        ["claims-intake", "claims-payments", "claims-analytics"],
        [
            "First Notice",
            "Adjuster",
            "Claim Payment",
            "Subrogation",
            "Fraud Score",
            "Salvage",
            "Repair Network",
            "Catastrophe",
            "Reserve",
            "Medical Bill",
        ],
    ),
    "Life and Annuities": (
        24,
        [12],
        ["life-admin", "annuity-ops"],
        [
            "Life Illustration",
            "Annuity Payout",
            "Beneficiary",
            "Medical Underwriting",
            "Policy Loan",
            "Commission Split",
        ],
    ),
    "Finance": (
        30,
        [12, 1],
        ["finance-systems", "treasury"],
        [
            "General Ledger",
            "Accounts Payable",
            "Premium Accounting",
            "Reinsurance",
            "Cash Management",
            "Statutory Reporting",
            "Tax",
            "Expense",
        ],
    ),
    "Distribution": (
        24,
        [11],
        ["agency-portal", "producer-mgmt"],
        ["Agent Portal", "Producer Licensing", "Lead Routing", "Commission", "Agency Contract", "Marketing Campaign"],
    ),
    "Actuarial": (
        14,
        [2],
        ["actuarial-models"],
        ["Pricing Model", "Loss Triangle", "Experience Study", "Capital Model"],
    ),
    "Human Resources": (10, [], ["people-systems"], ["Payroll", "Benefits", "Learning", "Recruiting", "Time Entry"]),
    "IT Shared Services": (
        20,
        [],
        ["platform-eng", "integration"],
        [
            "Service Desk",
            "Identity Sync",
            "Document Archive",
            "Print Stream",
            "File Transfer",
            "Email Archive",
            "API Gateway",
            "Job Scheduler",
        ],
    ),
}

SUFFIXES = [
    "Service",
    "Portal",
    "Engine",
    "API",
    "Batch",
    "Workbench",
    "Reporting",
    "Gateway",
    "Tracker",
    "Hub",
    "Console",
    "Loader",
    "Sync",
    "Viewer",
    "Calculator",
]

TEAM_SKILLS = {  # (cloud, containers) chosen so a few teams are clearly behind
    "policy-core": (2, 1),
    "auto-rating": (3, 3),
    "home-quote": (2, 2),
    "commercial-uw": (1, 0),
    "specialty-lines": (1, 1),
    "claims-intake": (2, 2),
    "claims-payments": (1, 1),
    "claims-analytics": (3, 2),
    "life-admin": (0, 0),
    "annuity-ops": (1, 0),
    "finance-systems": (1, 1),
    "treasury": (2, 1),
    "agency-portal": (3, 3),
    "producer-mgmt": (2, 1),
    "actuarial-models": (2, 2),
    "people-systems": (1, 0),
    "platform-eng": (3, 3),
    "integration": (2, 2),
    "mainframe-ops": (0, 0),
    "data-platform": (2, 1),
}
TEAM_UNAVAILABLE = {"life-admin": [5, 6], "finance-systems": [3], "claims-payments": [7]}
TEAM_CAPACITY = {"claims-payments": 3, "finance-systems": 3}  # contractors added to the two busiest teams

COTS_PRODUCTS = [  # (made-up product, has a SaaS equivalent)
    ("PayFlex HR", True),
    ("TalentDesk", True),
    ("LearnGrid", True),
    ("ServiceLoop ITSM", True),
    ("ArchiveVault", True),
    ("ExpensePilot", True),
    ("LedgerWorks", False),
    ("ClaimsVision 8", False),
    ("DocuForge", False),
    ("RateSmith", False),
    ("ReinsureOne", False),
    ("CampaignCraft", True),
]

STACKS = {  # stack: [(os, weight)], [(db, weight)]
    "Java": (
        [("RHEL 6", 1), ("RHEL 7", 4), ("RHEL 8", 4), ("RHEL 9", 1), ("Solaris 10", 1)],
        [("Oracle 11g", 2), ("Oracle 12c", 3), ("Oracle 19c", 3), ("PostgreSQL 13", 2), ("none", 1)],
    ),
    ".NET Framework": (
        [
            ("Windows Server 2008 R2", 2),
            ("Windows Server 2012 R2", 4),
            ("Windows Server 2016", 3),
            ("Windows Server 2019", 2),
        ],
        [("SQL Server 2008", 2), ("SQL Server 2014", 4), ("SQL Server 2019", 2), ("none", 1)],
    ),
    ".NET Core": (
        [("Windows Server 2019", 2), ("Windows Server 2022", 2), ("RHEL 8", 1)],
        [("SQL Server 2019", 3), ("PostgreSQL 13", 1)],
    ),
    "Python": ([("RHEL 8", 3), ("RHEL 9", 2), ("RHEL 7", 1)], [("PostgreSQL 13", 3), ("MySQL 8", 1), ("none", 1)]),
    "Node.js": ([("RHEL 8", 2), ("RHEL 9", 2)], [("PostgreSQL 13", 2), ("MySQL 8", 2), ("none", 1)]),
    "PHP": ([("RHEL 6", 1), ("RHEL 7", 2)], [("MySQL 5.7", 3)]),
    "COBOL (Micro Focus)": ([("AIX 7.1", 1)], [("DB2 LUW", 1)]),
}
STACK_WEIGHTS = [
    ("Java", 30),
    (".NET Framework", 26),
    (".NET Core", 10),
    ("Python", 10),
    ("Node.js", 7),
    ("PHP", 4),
    ("COBOL (Micro Focus)", 3),
]

DB_PORT = {"Oracle": 1521, "SQL Server": 1433, "PostgreSQL": 5432, "MySQL": 3306, "DB2": 50000}
NOISE_PORTS = {161, 9100, 5666, 10000, 9392, 389, 88, 53, 123, 8530, 636}

DAY_BYTES = {"heavy": (2e9, 20e9), "medium": (2e8, 2e9), "light": (5e6, 2e8)}
DAY_CONNS = {"heavy": (20_000, 200_000), "medium": (2_000, 20_000), "light": (50, 1_000)}


@dataclass
class SynthConfig:
    seed: int = 42
    observation_days: int = 14
    plan_start: date = date(2027, 1, 1)
    shared_db_consumers: int = 30
    mainframe_batch_apps: int = 12
    undocumented_rate: float = 0.25
    stale_documented: int = 15
    hardcoded_ip_apps: int = 25


def _pick(rng: random.Random, weighted: list[tuple[str, int]]) -> str:
    names, weights = zip(*weighted, strict=True)
    return rng.choices(names, weights=weights, k=1)[0]


def _db_port(db: str) -> int:
    for k, p in DB_PORT.items():
        if db.startswith(k):
            return p
    return 1521


class _IPs:
    def __init__(self):
        self.next = {}

    def take(self, subnet: str) -> str:
        n = self.next.get(subnet, 10)
        self.next[subnet] = n + 1
        return f"{subnet}.{n}"


def generate(cfg: SynthConfig | None = None) -> Estate:
    cfg = cfg or SynthConfig()
    rng = random.Random(cfg.seed)
    ips = _IPs()
    apps: dict[str, Application] = {}
    servers: dict[str, Server] = {}
    teams = {
        name: Team(
            name,
            c,
            k,
            capacity_per_wave=TEAM_CAPACITY.get(name, 3 if c >= 2 else 2),
            unavailable_waves=list(TEAM_UNAVAILABLE.get(name, [])),
        )
        for name, (c, k) in TEAM_SKILLS.items()
    }

    # ---- applications ----
    used_names: set[str] = set()
    n = 0
    bu_apps: dict[str, list[str]] = {}
    for bu, (count, freeze, bu_teams, nouns) in BUSINESS_UNITS.items():
        bu_apps[bu] = []
        for _ in range(count):
            n += 1
            while True:
                name = f"{rng.choice(nouns)} {rng.choice(SUFFIXES)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            cots = rng.random() < (0.45 if bu in ("Human Resources", "IT Shared Services", "Finance") else 0.15)
            product, saas = rng.choice(COTS_PRODUCTS) if cots else ("", False)
            stack = "COTS" if cots else _pick(rng, STACK_WEIGHTS)
            os_choices, db_choices = STACKS[
                ".NET Framework" if cots and rng.random() < 0.7 else ("Java" if cots else stack)
            ]
            os_name = _pick(rng, os_choices)
            db = _pick(rng, db_choices)
            crit = _pick(rng, [("1", 2), ("2", 4), ("3", 4), ("4", 2)])
            crit = int(crit)
            low_use = rng.random() < 0.14
            users = int(rng.lognormvariate(5.5, 1.2)) if not low_use else rng.randint(3, 45)
            ysc = round(rng.uniform(4, 9), 1) if low_use else round(rng.uniform(0.1, 6), 1)
            deploys = 0 if ysc > 2 else rng.randint(2, 60)
            comp = []
            lname = name.lower()
            if (
                bu in ("Personal Lines", "Commercial Lines", "Claims", "Life and Annuities", "Distribution")
                and rng.random() < 0.7
            ):
                comp.append("PII")
            if any(w in lname for w in ("payment", "billing", "cash")) or (bu == "Claims" and rng.random() < 0.1):
                comp.append("PCI")
            if any(w in lname for w in ("medical",)) or (bu == "Life and Annuities" and rng.random() < 0.3):
                comp.append("PHI")
            if bu == "Finance":
                comp.append("SOX")
            freeze_m = list(freeze)
            if rng.random() < 0.08:
                freeze_m.append(rng.randint(1, 12))
            app_id = f"APP-{n:03d}"
            apps[app_id] = Application(
                id=app_id,
                name=name,
                business_unit=bu,
                kind="standard",
                criticality=crit,
                owner_team=rng.choice(bu_teams),
                tech_stack=stack,
                os=os_name,
                db_engine=db,
                cots=cots,
                vendor_product=product,
                saas_equivalent=saas,
                data_gb=int(rng.lognormvariate(5.0, 1.4)) if db != "none" else rng.randint(5, 40),
                latency_sensitive=rng.random() < (0.35 if crit <= 2 else 0.1),
                compliance=sorted(set(comp)),
                freeze_months=sorted(set(freeze_m)),
                monthly_users=users,
                years_since_change=ysc,
                deploys_per_year=deploys,
                business_value=max(1, min(5, 6 - crit + rng.choice([-1, 0, 0, 1]))),
                documented_deps=[],
                hardcoded_ips=[],
            )
            bu_apps[bu].append(app_id)

    # two special apps: the shared Oracle database and the mainframe
    hub = Application(
        id="APP-249",
        name="Claims Data Hub",
        business_unit="Claims",
        kind="shared_database",
        criticality=1,
        owner_team="data-platform",
        tech_stack="Oracle PL/SQL",
        os="RHEL 7",
        db_engine="Oracle 19c",
        cots=False,
        vendor_product="",
        saas_equivalent=False,
        data_gb=18_000,
        latency_sensitive=True,
        compliance=["PCI", "PHI", "PII"],
        freeze_months=[8, 9, 10],
        monthly_users=0,
        years_since_change=0.5,
        deploys_per_year=12,
        business_value=5,
        documented_deps=[],
        hardcoded_ips=[],
    )
    mf = Application(
        id="APP-250",
        name="Policy Admin Mainframe",
        business_unit="Personal Lines",
        kind="mainframe",
        criticality=1,
        owner_team="mainframe-ops",
        tech_stack="COBOL/CICS",
        os="z/OS 2.5",
        db_engine="DB2 z/OS",
        cots=False,
        vendor_product="",
        saas_equivalent=False,
        data_gb=42_000,
        latency_sensitive=False,
        compliance=["PII", "SOX"],
        freeze_months=[3, 12],
        monthly_users=2400,
        years_since_change=0.3,
        deploys_per_year=24,
        business_value=5,
        documented_deps=[],
        hardcoded_ips=[],
    )
    apps[hub.id] = hub
    apps[mf.id] = mf
    standard = [a for a in apps if apps[a].kind == "standard"]

    # duplicates left over from an acquisition: low use, same job as another app
    for a in rng.sample(standard, 8):
        app = apps[a]
        twin = rng.choice([b for b in bu_apps[app.business_unit] if b != a])
        app.duplicate_of = twin
        app.monthly_users = rng.randint(2, 40)
        app.years_since_change = round(rng.uniform(4, 8), 1)
        app.deploys_per_year = 0

    # ---- servers ----
    subnet_of_bu = {bu: f"10.{20 + i}.{rng.randint(1, 9)}" for i, bu in enumerate(BUSINESS_UNITS)}
    sn = 0

    def add_server(
        app: Application | None,
        role: str,
        env: str,
        os_name: str,
        subnet: str,
        cores: int,
        ram: int,
        storage: int,
        physical: bool,
    ) -> Server:
        nonlocal sn
        sn += 1
        cpu = min(0.97, rng.betavariate(2, 6) * (0.5 if env == "nonprod" else 1.0))
        mem = min(0.97, rng.betavariate(4, 4) * (0.7 if env == "nonprod" else 1.0))
        prefix = "".join(w[0] for w in (app.name.split() if app else [role])).lower()
        s = Server(
            id=f"SRV-{sn:04d}",
            hostname=f"{prefix}{role[:2]}{sn:04d}{'n' if env == 'nonprod' else 'p'}",
            ip=ips.take(subnet),
            app_id=app.id if app else None,
            role=role,
            env=env,
            os=os_name,
            cores=cores,
            ram_gb=ram,
            cpu_p95=round(cpu, 3),
            mem_p95=round(mem, 3),
            storage_gb=storage,
            physical=physical,
            hw_age_years=rng.randint(1, 9),
        )
        servers[s.id] = s
        if app:
            app.server_ids.append(s.id)
        return s

    for a in standard:
        app = apps[a]
        subnet = subnet_of_bu[app.business_unit]
        unix = app.os.startswith(("AIX", "Solaris"))
        big = app.criticality <= 2
        for _ in range(rng.choice([0, 0, 1, 1, 2]) if not app.cots else rng.randint(0, 1)):
            add_server(app, "web", "prod", app.os, subnet, rng.choice([2, 4]), rng.choice([4, 8]), 80, unix)
        for _ in range(1 + (1 if big and rng.random() < 0.6 else 0)):
            c = rng.choice([4, 8, 8, 16])
            add_server(app, "app", "prod", app.os, subnet, c, c * rng.choice([2, 4]), 120, unix or rng.random() < 0.1)
        if app.db_engine != "none":
            c = rng.choice([4, 8, 16, 16, 32])
            add_server(
                app,
                "db",
                "prod",
                app.os,
                subnet,
                c,
                c * rng.choice([4, 8]),
                app.data_gb + 200,
                unix or rng.random() < 0.35,
            )
        for _ in range(rng.choice([0, 0, 1, 1, 2])):
            add_server(app, "app", "nonprod", app.os, subnet, rng.choice([2, 4]), 8, 100, False)
    for _ in range(2):
        add_server(hub, "db", "prod", hub.os, "10.30.1", 32, 512, 9500, True)
    for _ in range(2):
        add_server(hub, "db", "nonprod", hub.os, "10.30.1", 16, 128, 4000, False)
    for _ in range(2):
        add_server(mf, "mainframe", "prod", mf.os, "10.10.1", 64, 1024, 21000, True)
    infra = {}
    for role, count in (
        ("monitoring", 2),
        ("backup", 2),
        ("directory", 2),
        ("patch", 1),
        ("scanner", 1),
    ):
        infra[role] = [
            add_server(
                None,
                role,
                "prod",
                "Windows Server 2019" if role in ("directory", "patch") else "RHEL 8",
                "10.5.1",
                8,
                32,
                2000 if role == "backup" else 200,
                False,
            )
            for _ in range(count)
        ]

    # ---- ground-truth dependencies (consumer -> provider) with a weight class ----
    truth: dict[tuple[str, str], str] = {}
    for _bu, ids in bu_apps.items():
        pool = [a for a in ids if apps[a].kind == "standard"]
        rng.shuffle(pool)
        systems = []
        while pool:
            k = min(len(pool), rng.randint(3, 7))
            systems.append(pool[:k])
            pool = pool[k:]
        for sys_ in systems:
            for i in range(1, len(sys_)):  # a tree inside each system: tight, chatty coupling
                truth[(sys_[i], sys_[rng.randrange(i)])] = rng.choice(["heavy", "heavy", "medium"])
            if len(sys_) > 3 and rng.random() < 0.5:
                a, b = rng.sample(sys_, 2)
                truth.setdefault((a, b), "medium")
        for _ in range(len(systems)):  # lighter links between systems of the same unit
            s1, s2 = rng.sample(systems, 2) if len(systems) > 1 else (systems[0], systems[0])
            a, b = rng.choice(s1), rng.choice(s2)
            if a != b:
                truth.setdefault((a, b), rng.choice(["light", "medium"]))
    for _ in range(45):  # cross-unit integration links
        a, b = rng.sample(standard, 2)
        if apps[a].business_unit != apps[b].business_unit:
            truth.setdefault((a, b), "light")
    claims = [a for a in standard if apps[a].business_unit == "Claims"]
    others = [a for a in standard if apps[a].business_unit != "Claims"]
    hub_consumers = rng.sample(claims, 18) + rng.sample(others, cfg.shared_db_consumers - 18)
    for a in hub_consumers:
        truth[(a, hub.id)] = rng.choice(["heavy", "medium", "medium"])
    batch_apps = rng.sample([a for a in standard if a not in hub_consumers], cfg.mainframe_batch_apps)
    for a in batch_apps:
        truth[(a, mf.id)] = "batch"
    for a in rng.sample([a for a in standard if apps[a].business_unit == "Personal Lines"], 3):
        truth[(a, mf.id)] = "medium"  # online CICS calls over MQ
    for a in [x for x in standard if apps[x].duplicate_of]:  # duplicates have few, light ties
        for k in [k for k in truth if a in k and truth[k] == "heavy"]:
            truth[k] = "light"

    # ---- documented dependencies: incomplete and partly stale ----
    undocumented_hub = set(rng.sample(hub_consumers, 8))
    for (a, b), _cls in truth.items():
        if b == hub.id:
            if a in undocumented_hub:
                continue
        elif rng.random() < cfg.undocumented_rate:
            continue
        apps[a].documented_deps.append(b)
    stale = 0
    while stale < cfg.stale_documented:
        a, b = rng.sample(standard, 2)
        if (a, b) not in truth and (b, a) not in truth and b not in apps[a].documented_deps:
            apps[a].documented_deps.append(b)
            stale += 1
    for a in apps.values():
        a.documented_deps.sort()

    # ---- flows ----
    flows: list[Flow] = []
    days = cfg.observation_days

    def prod_servers(app_id: str, roles: tuple[str, ...]) -> list[Server]:
        return [servers[s] for s in apps[app_id].server_ids if servers[s].env == "prod" and servers[s].role in roles]

    def emit(src: Server, dst: Server | str, port: int, cls: str, proto: str = "tcp") -> None:
        dst_ip = dst if isinstance(dst, str) else dst.ip
        if cls == "batch":
            conns = days * rng.randint(1, 4)
            nbytes = int(days * rng.uniform(1e9, 6e9))
        else:
            conns = int(days * rng.uniform(*DAY_CONNS[cls]))
            nbytes = int(days * rng.uniform(*DAY_BYTES[cls]))
        flows.append(Flow(src.ip, dst_ip, port, proto, conns, nbytes))

    for (a, b), cls in truth.items():
        srcs = prod_servers(a, ("app", "batch")) or prod_servers(a, ("web", "app", "db"))
        if apps[b].kind == "mainframe":
            dsts, port = prod_servers(b, ("mainframe",)), (1364 if cls == "batch" else 1414)
        elif apps[b].kind == "shared_database":
            dsts, port = prod_servers(b, ("db",)), 1521
        elif rng.random() < 0.35 and prod_servers(b, ("db",)):  # direct reads from another app's database
            dsts, port = prod_servers(b, ("db",)), _db_port(apps[b].db_engine)
        else:
            dsts, port = (prod_servers(b, ("web", "app")) or prod_servers(b, ("db",))), rng.choice([443, 8443, 8080])
        src = rng.choice(srcs)
        for dst in dsts[: rng.randint(1, len(dsts))]:
            emit(src, dst, port, cls)
    for a in standard:  # intra-app tiers: web -> app -> db
        tiers = [prod_servers(a, ("web",)), prod_servers(a, ("app",)), prod_servers(a, ("db",))]
        tiers = [t for t in tiers if t]
        for up, down in zip(tiers, tiers[1:], strict=False):
            emit(
                rng.choice(up),
                rng.choice(down),
                8080 if down[0].role == "app" else _db_port(apps[a].db_engine),
                "heavy",
            )

    app_servers = [s for s in servers.values() if s.app_id]
    for s in app_servers:  # infrastructure noise
        mon = rng.choice(infra["monitoring"])
        flows.append(Flow(mon.ip, s.ip, 161, "udp", days * 288, days * 288 * 900))
        flows.append(Flow(mon.ip, s.ip, 9100, "tcp", days * 1440, days * 1440 * 6000))
        bkp = rng.choice(infra["backup"])
        flows.append(Flow(bkp.ip, s.ip, 10000, "tcp", days, int(days * s.storage_gb * 1e9 * 0.04)))
        dc = rng.choice(infra["directory"])
        flows.append(Flow(s.ip, dc.ip, 389, "tcp", days * rng.randint(100, 3000), days * rng.randint(10**5, 10**7)))
        flows.append(Flow(s.ip, dc.ip, 53, "udp", days * rng.randint(500, 5000), days * rng.randint(10**5, 10**6)))
        if s.os.startswith("Windows"):
            flows.append(Flow(s.ip, infra["patch"][0].ip, 8530, "tcp", days * 4, days * rng.randint(10**7, 10**8)))
    scanner = infra["scanner"][0]
    for s in rng.sample(app_servers, 300):
        for port in rng.sample(range(1, 1024), 3):
            flows.append(Flow(scanner.ip, s.ip, port, "tcp", 1, 60))
    for _ in range(60):  # stray one-off connections between random app servers
        a, b = rng.sample(app_servers, 2)
        if a.app_id != b.app_id:
            flows.append(
                Flow(a.ip, b.ip, rng.choice([22, 3389, 135]), "tcp", rng.randint(1, 3), rng.randint(2_000, 400_000))
            )

    # servers nobody put in the CMDB
    shadow_sql, shadow_share = "10.88.14.21", "10.88.14.40"
    for a in rng.sample(standard, 4):
        src = rng.choice(prod_servers(a, ("app", "web", "db")))
        emit(src, shadow_sql, 1433, "medium")
    for a in rng.sample(standard, 3):
        src = rng.choice(prod_servers(a, ("app", "web", "db")))
        emit(src, shadow_share, 445, "light")

    # IP literals found in config files
    with_deps = [a for a in standard if any(k[0] == a for k in truth)]
    for a in rng.sample(with_deps, cfg.hardcoded_ip_apps):
        provs = [b for (x, b) in truth if x == a]
        b = rng.choice(provs)
        targets = prod_servers(b, ("db", "app", "web", "mainframe"))
        if targets:
            apps[a].hardcoded_ips = sorted({rng.choice(targets).ip})

    flows.sort(key=lambda f: (f.src_ip, f.dst_ip, f.port))
    return Estate(
        company=COMPANY,
        observation_days=days,
        plan_start=cfg.plan_start,
        apps=apps,
        servers=servers,
        flows=flows,
        teams=teams,
        truth_deps=set(truth),
    )
