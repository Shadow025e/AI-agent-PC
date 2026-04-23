"""Data models for monitoring and alerts."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ProcessUsage:
    pid: int
    name: str
    cpu_percent: float | None
    ram_percent: float | None


@dataclass(frozen=True)
class SystemSnapshot:
    cpu_percent: float | None
    ram_percent: float | None
    disk_percent: float | None
    battery_percent: float | None
    battery_status: str | None


@dataclass
class Alert:
    level: AlertLevel
    category: str
    message: str
    fingerprint: str
    details: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
