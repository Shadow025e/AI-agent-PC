"""SQLite bootstrap for local-only runtime."""

from pathlib import Path
import sqlite3


def initialize_sqlite(db_path: Path) -> None:
    """Initialize local SQLite database and run bootstrap migration.

    TODO: Replace with versioned migration runner.
    """

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL,
                payload TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
