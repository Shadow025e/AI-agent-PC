"""Base runtime configuration for local scaffold."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Application paths and local runtime defaults.

    TODO: Expand with structured settings validation and environment overrides.
    """

    project_root: Path
    data_dir: Path
    db_path: Path


def load_config(project_root: Path | None = None) -> AppConfig:
    root = project_root or Path.cwd()
    data_dir = root / ".data"
    db_path = data_dir / "agent.db"
    return AppConfig(project_root=root, data_dir=data_dir, db_path=db_path)
