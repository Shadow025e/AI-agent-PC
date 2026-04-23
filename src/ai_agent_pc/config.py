"""Base runtime configuration for local scaffold."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MonitoringConfig:
    """Tunable local monitoring thresholds and cadence."""

    polling_interval_seconds: float = 5.0
    high_cpu_percent: float = 85.0
    high_ram_percent: float = 85.0
    high_disk_percent: float = 92.0
    high_process_cpu_percent: float = 90.0
    high_process_ram_percent: float = 25.0
    spike_delta_percent: float = 30.0
    repeated_high_count: int = 3
    repeated_high_window_seconds: int = 300
    frequent_crash_threshold: int = 3
    dedup_window_seconds: int = 120


@dataclass(frozen=True)
class AppConfig:
    """Application paths and local runtime defaults."""

    project_root: Path
    data_dir: Path
    db_path: Path
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)


def load_config(project_root: Path | None = None) -> AppConfig:
    root = project_root or Path.cwd()
    data_dir = root / ".data"
    db_path = data_dir / "agent.db"
    return AppConfig(project_root=root, data_dir=data_dir, db_path=db_path)
