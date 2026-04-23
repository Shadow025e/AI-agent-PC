"""SQLite bootstrap and repositories for local-only runtime."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from ai_agent_pc.monitoring.models import Alert


def initialize_sqlite(db_path: Path) -> None:
    """Initialize local SQLite database and run bootstrap migration."""

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
            "CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint)"
        )
        conn.commit()


class AuditLogger:
    """Simple audit/event logger backed by app_events."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def log(self, event: str, payload: dict[str, object]) -> None:
        initialize_sqlite(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO app_events(event, payload) VALUES(?, ?)",
                (event, json.dumps(payload, sort_keys=True)),
            )
            conn.commit()


    def list_events(self, limit: int = 100) -> list[dict[str, object]]:
        initialize_sqlite(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
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


class AlertRepository:
    """Persists and queries monitoring alerts, with deduplication support."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def store_alert(self, alert: Alert, dedup_window_seconds: int) -> bool:
        """Store alert and deduplicate by fingerprint in a rolling time window.

        Returns True when a new row is inserted, False when an existing alert is updated.
        """

        initialize_sqlite(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
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
        initialize_sqlite(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
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
