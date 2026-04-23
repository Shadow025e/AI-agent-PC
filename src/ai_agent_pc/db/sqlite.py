"""SQLite bootstrap and repositories for local-only runtime."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from ai_agent_pc.monitoring.models import Alert
from ai_agent_pc.routines.models import Routine, RoutineStep

_INITIALIZED_DB_PATHS: set[Path] = set()


class SQLiteDatabase:
    """Shared SQLite access layer that enforces schema initialization."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self, *, row_factory: bool = False) -> sqlite3.Connection:
        initialize_sqlite(self.db_path)
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = sqlite3.Row
        return conn


def initialize_sqlite(db_path: Path) -> None:
    """Initialize local SQLite database and run bootstrap migration."""

    db_path = db_path.resolve()
    if db_path in _INITIALIZED_DB_PATHS:
        return
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                details TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trusted_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(target_type, value)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                built_in INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routine_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine_id INTEGER NOT NULL,
                step_order INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                args_json TEXT,
                FOREIGN KEY(routine_id) REFERENCES routines(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_routine_steps_routine_id ON routine_steps(routine_id)")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_routine_steps_unique ON routine_steps(routine_id, step_order)"
        )
        conn.commit()
    _seed_default_trusted_targets(db_path)
    _seed_builtin_routines(db_path)
    _INITIALIZED_DB_PATHS.add(db_path)


class AuditLogger:
    """Simple audit/event logger backed by app_events."""

    def __init__(self, db_path: Path) -> None:
        self._db = SQLiteDatabase(db_path)

    def log(self, event: str, payload: dict[str, object]) -> None:
        with self._db.connect() as conn:
            conn.execute(
                "INSERT INTO app_events(event, payload) VALUES(?, ?)",
                (event, json.dumps(payload, sort_keys=True)),
            )
            conn.commit()

    def list_events(self, limit: int = 100) -> list[dict[str, object]]:
        with self._db.connect(row_factory=True) as conn:
            rows = conn.execute(
                """
                SELECT id, event, payload, created_at
                FROM app_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        events: list[dict[str, object]] = []
        for row in rows:
            payload = dict(row)
            payload["payload"] = json.loads(payload["payload"] or "{}")
            events.append(payload)
        return events


class TrustedTargetRepository:
    """Trusted apps/paths allowlist storage."""

    def __init__(self, db_path: Path) -> None:
        self._db = SQLiteDatabase(db_path)

    def list_trusted_apps(self) -> list[str]:
        return self._list_by_type("app")

    def list_trusted_paths(self) -> list[str]:
        return self._list_by_type("path")

    def is_app_trusted(self, app: str) -> bool:
        app_norm = app.strip().lower()
        return app_norm in {a.lower() for a in self.list_trusted_apps()}

    def _list_by_type(self, target_type: str) -> list[str]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT value FROM trusted_targets WHERE target_type = ? ORDER BY value ASC",
                (target_type,),
            ).fetchall()
        return [str(row[0]) for row in rows]


class RoutineRepository:
    """Routine definitions + steps persistence for extensible workflows."""

    def __init__(self, db_path: Path) -> None:
        self._db = SQLiteDatabase(db_path)

    def list_routines(self) -> list[Routine]:
        with self._db.connect(row_factory=True) as conn:
            routine_rows = conn.execute(
                "SELECT id, name, description, built_in FROM routines ORDER BY name ASC"
            ).fetchall()
            steps = conn.execute(
                "SELECT id, routine_id, step_order, tool_name, args_json FROM routine_steps ORDER BY routine_id ASC, step_order ASC"
            ).fetchall()

        steps_by_routine: dict[int, list[RoutineStep]] = {}
        for row in steps:
            steps_by_routine.setdefault(int(row["routine_id"]), []).append(
                RoutineStep(
                    id=int(row["id"]),
                    tool_name=str(row["tool_name"]),
                    args=json.loads(row["args_json"] or "{}"),
                )
            )

        routines: list[Routine] = []
        for row in routine_rows:
            routine_id = int(row["id"])
            routines.append(
                Routine(
                    id=routine_id,
                    name=str(row["name"]),
                    description=str(row["description"]),
                    built_in=bool(row["built_in"]),
                    steps=steps_by_routine.get(routine_id, []),
                )
            )
        return routines

    def get_routine(self, name: str) -> Routine | None:
        for routine in self.list_routines():
            if routine.name == name:
                return routine
        return None


class AlertRepository:
    """Persists and queries monitoring alerts, with deduplication support."""

    def __init__(self, db_path: Path) -> None:
        self._db = SQLiteDatabase(db_path)

    def store_alert(self, alert: Alert, dedup_window_seconds: int) -> bool:
        """Store alert and deduplicate by fingerprint in a rolling time window.

        Returns True when a new row is inserted, False when an existing alert is updated.
        """

        with self._db.connect(row_factory=True) as conn:
            existing = conn.execute(
                """
                SELECT id, last_seen, occurrence_count
                FROM alerts
                WHERE fingerprint = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (alert.fingerprint,),
            ).fetchone()

            if existing is not None:
                last_seen = _parse_iso8601(existing["last_seen"])
                if alert.created_at - last_seen <= timedelta(seconds=dedup_window_seconds):
                    conn.execute(
                        """
                        UPDATE alerts
                        SET last_seen = ?, occurrence_count = ?
                        WHERE id = ?
                        """,
                        (
                            alert.created_at.isoformat(),
                            int(existing["occurrence_count"]) + 1,
                            int(existing["id"]),
                        ),
                    )
                    conn.commit()
                    return False

            conn.execute(
                """
                INSERT INTO alerts(
                    level, category, message, fingerprint, details, first_seen, last_seen, occurrence_count
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.level.value,
                    alert.category,
                    alert.message,
                    alert.fingerprint,
                    json.dumps(alert.details, sort_keys=True),
                    alert.created_at.isoformat(),
                    alert.created_at.isoformat(),
                    1,
                ),
            )
            conn.commit()
            return True

    def list_alerts(self, limit: int = 100) -> list[dict[str, object]]:
        with self._db.connect(row_factory=True) as conn:
            rows = conn.execute(
                """
                SELECT id, level, category, message, fingerprint, details, first_seen, last_seen, occurrence_count
                FROM alerts
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        alerts: list[dict[str, object]] = []
        for row in rows:
            payload = dict(row)
            payload["details"] = json.loads(payload["details"] or "{}")
            alerts.append(payload)
        return alerts


def _parse_iso8601(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _seed_default_trusted_targets(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        trusted_defaults = [
            ("app", "notes"),
            ("app", "calendar"),
            ("app", "vscode"),
            ("app", "terminal"),
            ("path", str((Path.home() / "Documents").resolve())),
            ("path", str((Path.home() / "Projects").resolve())),
        ]
        for row in trusted_defaults:
            conn.execute("INSERT OR IGNORE INTO trusted_targets(target_type, value) VALUES(?, ?)", row)
        conn.commit()


def _seed_builtin_routines(db_path: Path) -> None:
    routines = [
        (
            "Study Mode",
            "Open approved study apps/folder and optionally show system status.",
            [
                (1, "open_trusted_app", {"app": "notes"}),
                (2, "open_trusted_app", {"app": "calendar"}),
                (3, "open_trusted_folder", {"path": str((Path.home() / "Documents").resolve())}),
                (4, "get_system_status", {}),
            ],
        ),
        (
            "Coding Mode",
            "Open approved coding apps/folder and optionally show resource usage.",
            [
                (1, "open_trusted_app", {"app": "vscode"}),
                (2, "open_trusted_app", {"app": "terminal"}),
                (3, "open_trusted_folder", {"path": str((Path.home() / "Projects").resolve())}),
                (4, "list_processes", {"limit": 8}),
            ],
        ),
        (
            "Low Resource Mode",
            "Show heavy resource usage and safe close-app suggestion placeholder.",
            [
                (1, "list_processes", {"limit": 10}),
                (2, "suggest_close_non_critical_apps", {}),
            ],
        ),
    ]

    with sqlite3.connect(db_path) as conn:
        for name, description, steps in routines:
            conn.execute(
                "INSERT OR IGNORE INTO routines(name, description, built_in) VALUES(?, ?, 1)",
                (name, description),
            )
            row = conn.execute("SELECT id FROM routines WHERE name = ?", (name,)).fetchone()
            assert row is not None
            routine_id = int(row[0])
            for order, tool, args in steps:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO routine_steps(routine_id, step_order, tool_name, args_json)
                    VALUES(?, ?, ?, ?)
                    """,
                    (routine_id, order, tool, json.dumps(args, sort_keys=True)),
                )
        conn.commit()
