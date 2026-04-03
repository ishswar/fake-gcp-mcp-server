"""
GCP Compute MCP Server - Fake Data Generator

Generates deterministic fake GCP Compute Engine data with seed=42.
All timestamps are relative to anchor: 2026-03-10T12:00:00Z
"""

import random
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional

# Seed for deterministic generation
SEED = 42

# Anchor timestamp - all times relative to this
ANCHOR_TIME = datetime(2026, 3, 10, 12, 0, 0)  # Used for static data (projects, VMs, logs)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Project:
    project_id: str
    project_number: str
    name: str
    billing_account: str
    owner_email: str
    created_at: str
    labels: dict
    zones: list

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Zone:
    zone_id: str
    region: str
    project_id: str
    vm_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VM:
    vm_id: str
    instance_id: str
    name: str
    project_id: str
    zone: str
    machine_type: str
    vcpus: int
    memory_gb: float
    status: str
    internal_ip: str
    external_ip: Optional[str]
    tags: list
    labels: dict
    boot_disk_gb: int
    os_image: str
    owner_email: str
    created_at: str
    last_start_timestamp: Optional[str]
    self_link: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class User:
    user_id: str
    email: str
    display_name: str
    role: str
    project_id: str
    joined_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DataPoint:
    timestamp: str
    value: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LogEntry:
    log_id: str
    vm_id: str
    project_id: str
    zone: str
    event_type: str
    timestamp: str
    initiated_by: str
    message: str
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Configuration Constants
# =============================================================================

PROJECTS_CONFIG = [
    {"project_id": "proj-alpha-7x2k", "project_number": "proj-num-100001", "name": "Alpha Platform", "labels": {"env": "prod", "team": "platform"}, "vm_count": 28},
    {"project_id": "proj-beta-3m9p", "project_number": "proj-num-100002", "name": "Beta Analytics", "labels": {"env": "staging", "team": "analytics"}, "vm_count": 15},
    {"project_id": "proj-gamma-5r8t", "project_number": "proj-num-100003", "name": "Gamma ML Workloads", "labels": {"env": "prod", "team": "ml"}, "vm_count": 32},
    {"project_id": "proj-delta-2w4q", "project_number": "proj-num-100004", "name": "Delta Dev Sandbox", "labels": {"env": "dev", "team": "dev"}, "vm_count": 12},
    {"project_id": "proj-epsilon-9f1v", "project_number": "proj-num-100005", "name": "Epsilon Data Pipeline", "labels": {"env": "prod", "team": "data"}, "vm_count": 24},
]

ZONE_POOL = [
    "us-west1-a", "us-west1-b",
    "us-west2-a", "us-west2-b",
    "us-east1-b", "us-east1-c",
    "asia-northeast1-a", "asia-northeast1-b",
]

MACHINE_TYPES = [
    {"type": "e2-micro", "vcpus": 2, "memory_gb": 1.0},
    {"type": "e2-medium", "vcpus": 2, "memory_gb": 4.0},
    {"type": "n1-standard-2", "vcpus": 2, "memory_gb": 7.5},
    {"type": "n1-standard-4", "vcpus": 4, "memory_gb": 15.0},
    {"type": "n2-standard-4", "vcpus": 4, "memory_gb": 16.0},
    {"type": "n2-highmem-4", "vcpus": 4, "memory_gb": 32.0},
    {"type": "c2-standard-8", "vcpus": 8, "memory_gb": 32.0},
]

VM_NAME_PREFIXES = [
    "web-server", "api-gateway", "db-replica", "batch-worker", "ml-trainer",
    "data-pipeline", "cache-node", "log-collector", "monitoring", "scheduler"
]

VM_TAG_POOL = [
    "http-server", "https-server", "prod", "staging", "ssh", "internal",
    "load-balanced", "monitoring", "kafka-node", "db-server"
]

VM_LABEL_TEAMS = ["backend", "frontend", "data", "ml", "devops", "platform"]
VM_LABEL_ENVS = ["prod", "staging", "dev"]

OS_IMAGES = [
    "debian-cloud/debian-11",
    "ubuntu-os-cloud/ubuntu-2204-lts",
    "centos-cloud/centos-stream-9",
    "rocky-linux-cloud/rocky-linux-9",
]

USER_FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack"]
USER_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson"]

def generate_status_distribution(vm_count: int) -> list[str]:
    """Generate status distribution for a given VM count with realistic proportions."""
    # Roughly: 60-75% RUNNING, 15-25% STOPPED, 5-15% TERMINATED
    running_pct = random.uniform(0.60, 0.75)
    stopped_pct = random.uniform(0.15, 0.25)
    # Remaining goes to TERMINATED

    running = int(vm_count * running_pct)
    stopped = int(vm_count * stopped_pct)
    terminated = vm_count - running - stopped

    # Ensure at least 1 of each if vm_count allows
    if vm_count >= 3:
        running = max(1, running)
        stopped = max(1, stopped)
        terminated = max(1, terminated)
        # Rebalance if we went over
        total = running + stopped + terminated
        if total > vm_count:
            running -= (total - vm_count)

    statuses = ["RUNNING"] * running + ["STOPPED"] * stopped + ["TERMINATED"] * terminated
    random.shuffle(statuses)
    return statuses


# =============================================================================
# Helper Functions
# =============================================================================

def random_hex(length: int) -> str:
    """Generate random hex string of given length."""
    return ''.join(random.choice('0123456789abcdef') for _ in range(length))


def random_numeric_string(length: int) -> str:
    """Generate random numeric string of given length."""
    return ''.join(random.choice('0123456789') for _ in range(length))


def iso_timestamp(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def random_past_date(days_min: int, days_max: int) -> datetime:
    """Generate random datetime between days_min and days_max before anchor."""
    days = random.randint(days_min, days_max)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    return ANCHOR_TIME - timedelta(days=days, hours=hours, minutes=minutes)


# =============================================================================
# Generation Functions
# =============================================================================

def generate_projects() -> list[Project]:
    """Generate all 5 projects with assigned zones."""
    projects = []

    for cfg in PROJECTS_CONFIG:
        # Assign 3-4 zones per project
        num_zones = random.choice([3, 4])
        zones = random.sample(ZONE_POOL, num_zones)

        # Random billing account
        billing_suffix = random_hex(6).upper()
        billing_account = f"BILACCT-{cfg['labels']['team'].upper()}-{billing_suffix}"

        # Owner email from first user (will generate users later)
        owner_email = f"owner.{cfg['project_id'].split('-')[1]}@company.com"

        # Created 1-3 years before anchor
        created_at = random_past_date(365, 365 * 3)

        project = Project(
            project_id=cfg["project_id"],
            project_number=cfg["project_number"],
            name=cfg["name"],
            billing_account=billing_account,
            owner_email=owner_email,
            created_at=iso_timestamp(created_at),
            labels=cfg["labels"],
            zones=zones
        )
        projects.append(project)

    return projects


def generate_zones_for_project(project: Project) -> list[Zone]:
    """Generate Zone objects for a project (vm_count set later)."""
    zones = []
    for zone_id in project.zones:
        region = "-".join(zone_id.split("-")[:-1])
        zones.append(Zone(
            zone_id=zone_id,
            region=region,
            project_id=project.project_id,
            vm_count=0
        ))
    return zones


def generate_users_for_project(project_id: str, count: int = None) -> list[User]:
    """Generate 6-8 users for a project."""
    if count is None:
        count = random.randint(6, 8)

    users = []
    used_names = set()

    for i in range(count):
        # Generate unique name combination
        while True:
            first = random.choice(USER_FIRST_NAMES)
            last = random.choice(USER_LAST_NAMES)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break

        email = f"{first.lower()}.{last.lower()}@company.com"

        # First user is owner, rest random roles
        if i == 0:
            role = "owner"
        else:
            role = random.choice(["editor", "viewer", "compute.admin"])

        # Joined 6-18 months before anchor
        joined_at = random_past_date(180, 540)

        user = User(
            user_id=f"usr-{random_hex(6)}",
            email=email,
            display_name=f"{first} {last}",
            role=role,
            project_id=project_id,
            joined_at=iso_timestamp(joined_at)
        )
        users.append(user)

    return users


def generate_vms_for_project(project: Project, users: list[User], vm_count: int) -> list[VM]:
    """Generate VMs for a project distributed across zones."""
    vms = []
    zones = project.zones
    num_zones = len(zones)

    # Distribute VMs across zones
    base_per_zone = vm_count // num_zones
    remainder = vm_count % num_zones
    zone_vm_counts = [base_per_zone + (1 if i < remainder else 0) for i in range(num_zones)]

    # Generate status distribution for this project's VM count
    statuses = generate_status_distribution(vm_count)
    status_idx = 0

    vm_index = 0
    for zone_idx, zone_id in enumerate(zones):
        zone_vm_count = zone_vm_counts[zone_idx]

        for _ in range(zone_vm_count):
            # VM identifiers
            vm_id = f"vm-{random_hex(8)}"
            instance_id = random_numeric_string(19)

            # Name: prefix-env-XX
            prefix = random.choice(VM_NAME_PREFIXES)
            env = project.labels.get("env", "prod")
            name = f"{prefix}-{env}-{vm_index + 1:02d}"

            # Machine type
            mt = random.choice(MACHINE_TYPES)

            # Status
            status = statuses[status_idx]
            status_idx += 1

            # IPs
            internal_ip = f"10.{zone_idx * 2}.{random.randint(1, 254)}.{random.randint(1, 254)}"

            # External IP: None for 20% of VMs and ALL STOPPED/TERMINATED
            if status in ["STOPPED", "TERMINATED"]:
                external_ip = None
            elif random.random() < 0.2:
                external_ip = None
            else:
                external_ip = f"34.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

            # Tags and labels
            tags = random.sample(VM_TAG_POOL, random.randint(2, 3))
            labels = {
                "team": random.choice(VM_LABEL_TEAMS),
                "env": project.labels.get("env", "prod")
            }

            # Disk and OS
            boot_disk_gb = random.choice([50, 100, 200, 500])
            os_image = random.choice(OS_IMAGES)

            # Owner
            owner_email = random.choice(users).email

            # Created time
            created_at = random_past_date(30, 365)

            # Last start timestamp based on status
            if status == "RUNNING":
                last_start = random_past_date(3, 14)
            elif status == "STOPPED":
                last_start = random_past_date(1, 5)
            else:  # TERMINATED
                last_start = random_past_date(7, 30)

            # Self link
            self_link = f"https://www.googleapis.com/compute/v1/projects/{project.project_id}/zones/{zone_id}/instances/{name}"

            vm = VM(
                vm_id=vm_id,
                instance_id=instance_id,
                name=name,
                project_id=project.project_id,
                zone=zone_id,
                machine_type=mt["type"],
                vcpus=mt["vcpus"],
                memory_gb=mt["memory_gb"],
                status=status,
                internal_ip=internal_ip,
                external_ip=external_ip,
                tags=tags,
                labels=labels,
                boot_disk_gb=boot_disk_gb,
                os_image=os_image,
                owner_email=owner_email,
                created_at=iso_timestamp(created_at),
                last_start_timestamp=iso_timestamp(last_start),
                self_link=self_link
            )
            vms.append(vm)
            vm_index += 1

    return vms


def generate_performance_data(vm: VM) -> dict:
    """
    Generate 288 data points (5-min intervals, 24 hours) for CPU, memory, disk.
    Returns dict with keys: "cpu", "memory", "disk", each containing list of DataPoint.
    """
    data = {"cpu": [], "memory": [], "disk": []}

    # Per-VM random base values for memory and disk
    memory_base = random.uniform(45, 75)
    disk_base = random.uniform(30, 80)

    # Parse last_start_timestamp to determine when VM stopped
    if vm.last_start_timestamp:
        last_start = datetime.strptime(vm.last_start_timestamp, "%Y-%m-%dT%H:%M:%SZ")
    else:
        last_start = datetime.now() - timedelta(days=30)

    # Use current time so data always looks fresh (no restart needed)
    now = datetime.now()

    for i in range(288):
        # Timestamp: now - 24h + i*5min
        ts = now - timedelta(hours=24) + timedelta(minutes=i * 5)
        timestamp = iso_timestamp(ts)

        # For STOPPED/TERMINATED VMs, values are None after they stopped
        if vm.status in ["STOPPED", "TERMINATED"] and ts > last_start:
            data["cpu"].append(DataPoint(timestamp=timestamp, value=None))
            data["memory"].append(DataPoint(timestamp=timestamp, value=None))
            data["disk"].append(DataPoint(timestamp=timestamp, value=None))
            continue

        # CPU: sinusoidal daily pattern with noise
        hour = (i * 5) / 60  # fractional hour of day (0-24)
        cpu_base = 15 + 50 * (0.5 * math.sin(2 * math.pi * (hour - 6) / 24) +
                              0.3 * math.sin(2 * math.pi * (hour - 14) / 12))
        cpu_value = max(0, min(100, cpu_base + random.gauss(0, 8)))

        # Memory: steady with slow variation
        mem_variation = 10 * math.sin(2 * math.pi * i / 288)
        mem_value = max(20, min(100, memory_base + mem_variation + random.gauss(0, 3)))

        # Disk: slow increase with tiny noise
        disk_fill = i * 0.01  # gradual fill
        disk_value = max(0, min(100, disk_base + disk_fill + random.gauss(0, 1)))

        data["cpu"].append(DataPoint(timestamp=timestamp, value=round(cpu_value, 2)))
        data["memory"].append(DataPoint(timestamp=timestamp, value=round(mem_value, 2)))
        data["disk"].append(DataPoint(timestamp=timestamp, value=round(disk_value, 2)))

    return data


def generate_logs_for_vm(vm: VM, users: list[User]) -> list[LogEntry]:
    """Generate 7 days of event history for a VM."""
    logs = []
    user_emails = [u.email for u in users]

    def create_log(event_type: str, ts: datetime, initiated_by: str, message: str, severity: str) -> LogEntry:
        return LogEntry(
            log_id=f"log-{random_hex(8)}",
            vm_id=vm.vm_id,
            project_id=vm.project_id,
            zone=vm.zone,
            event_type=event_type,
            timestamp=iso_timestamp(ts),
            initiated_by=initiated_by,
            message=message,
            severity=severity
        )

    if vm.status == "RUNNING":
        # START event 3-14 days ago
        start_time = random_past_date(3, 14)
        logs.append(create_log(
            "START", start_time,
            random.choice(user_emails),
            "Instance started successfully",
            "INFO"
        ))

        # 0-2 RESTART events
        num_restarts = random.randint(0, 2)
        for _ in range(num_restarts):
            restart_time = start_time + timedelta(hours=random.randint(1, 72))
            if restart_time < ANCHOR_TIME:
                messages = [
                    "Instance restarted due to OS update",
                    "Auto-restart triggered by health check failure",
                    "Manual restart requested"
                ]
                logs.append(create_log(
                    "RESTART", restart_time,
                    random.choice(["system", "auto-scaler"] + user_emails),
                    random.choice(messages),
                    "WARNING"
                ))

        # 0-1 WARNING/ERROR events
        if random.random() < 0.3:
            error_time = start_time + timedelta(hours=random.randint(24, 168))
            if error_time < ANCHOR_TIME:
                error_messages = [
                    "Disk I/O error detected",
                    "High memory pressure warning",
                    "Network interface reset"
                ]
                logs.append(create_log(
                    "ERROR" if random.random() < 0.5 else "WARNING",
                    error_time,
                    "system",
                    random.choice(error_messages),
                    "ERROR" if random.random() < 0.5 else "WARNING"
                ))

    elif vm.status == "STOPPED":
        # START event 3-7 days ago
        start_time = random_past_date(3, 7)
        logs.append(create_log(
            "START", start_time,
            random.choice(user_emails),
            "Instance started successfully",
            "INFO"
        ))

        # STOP event within last 24 hours
        stop_time = random_past_date(0, 1)
        stop_messages = [
            f"Instance stopped by {random.choice(user_emails)}",
            "Scheduled maintenance shutdown",
            "Instance stopped by auto-scaler due to low utilization"
        ]
        logs.append(create_log(
            "STOP", stop_time,
            random.choice(["system", "auto-scaler", "maintenance"] + user_emails),
            random.choice(stop_messages),
            "INFO"
        ))

        # Maybe 1 WARNING before stop
        if random.random() < 0.3:
            warn_time = start_time + timedelta(hours=random.randint(12, 48))
            if warn_time < stop_time:
                logs.append(create_log(
                    "WARNING", warn_time,
                    "system",
                    "High memory pressure detected",
                    "WARNING"
                ))

    else:  # TERMINATED
        # START event 7-30 days ago
        start_time = random_past_date(7, 30)
        logs.append(create_log(
            "START", start_time,
            random.choice(user_emails),
            "Instance started successfully",
            "INFO"
        ))

        # ERROR or STOP event at termination
        term_time = start_time + timedelta(days=random.randint(1, 7))
        if random.random() < 0.5:
            term_messages = [
                "Out of memory: kernel panic",
                "Disk failure: instance terminated",
                "Critical hardware error detected"
            ]
            logs.append(create_log(
                "ERROR", term_time,
                "system",
                random.choice(term_messages),
                "ERROR"
            ))
        else:
            logs.append(create_log(
                "STOP", term_time,
                random.choice(["system", "maintenance"]),
                "Instance terminated due to preemption",
                "INFO"
            ))

    # Sort logs chronologically (oldest first)
    logs.sort(key=lambda x: x.timestamp)

    return logs


def generate_all_data() -> dict:
    """
    Generate all fake GCP data.
    Returns dict with keys: projects, zones, vms, users, performance, logs
    """
    random.seed(SEED)

    projects = generate_projects()

    zones = {}  # project_id -> list[Zone]
    users = {}  # project_id -> list[User]
    vms = {}    # project_id -> list[VM]
    performance = {}  # vm_id -> {"cpu": [...], "memory": [...], "disk": [...]}
    logs = {}   # vm_id -> list[LogEntry]

    for project in projects:
        # Generate zones
        project_zones = generate_zones_for_project(project)

        # Generate users
        project_users = generate_users_for_project(project.project_id)

        # Update project owner_email to first user
        project.owner_email = project_users[0].email

        # Get VM count for this project from config
        project_cfg = next(c for c in PROJECTS_CONFIG if c["project_id"] == project.project_id)
        vm_count = project_cfg.get("vm_count", 25)

        # Generate VMs
        project_vms = generate_vms_for_project(project, project_users, vm_count)

        # Update zone vm_counts
        zone_counts = {}
        for vm in project_vms:
            zone_counts[vm.zone] = zone_counts.get(vm.zone, 0) + 1
        for z in project_zones:
            z.vm_count = zone_counts.get(z.zone_id, 0)

        # Generate performance and logs for each VM
        for vm in project_vms:
            performance[vm.vm_id] = generate_performance_data(vm)
            logs[vm.vm_id] = generate_logs_for_vm(vm, project_users)

        zones[project.project_id] = project_zones
        users[project.project_id] = project_users
        vms[project.project_id] = project_vms

    return {
        "projects": projects,
        "zones": zones,
        "vms": vms,
        "users": users,
        "performance": performance,
        "logs": logs
    }


if __name__ == "__main__":
    # Test generation
    data = generate_all_data()
    print(f"Generated {len(data['projects'])} projects")
    total_vms = sum(len(v) for v in data['vms'].values())
    print(f"Generated {total_vms} VMs")
    total_users = sum(len(u) for u in data['users'].values())
    print(f"Generated {total_users} users")
    print(f"Generated {len(data['performance'])} performance records")
    print(f"Generated {len(data['logs'])} log records")

    # Sample output
    print("\nSample project:", data['projects'][0].project_id)
    print("Sample VM:", data['vms'][data['projects'][0].project_id][0].name)
