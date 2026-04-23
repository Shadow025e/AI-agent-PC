from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models import AuditLogEntry


class AuditLogger:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def write(self, entry: AuditLogEntry) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_logs (
                timestamp,
                tool_name,
                risk_level,
                request_summary,
                result_status,
                detail
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry.timestamp.isoformat(),
                entry.tool_name,
                entry.risk_level.value,
                entry.request_summary,
                entry.result_status.value,
                entry.detail,
            ),
        )
        self._conn.commit()

    def write_now(
        self,
        *,
        tool_name: str,
        risk_level: str,
        request_summary: str,
        result_status: str,
        detail: str,
    ) -> None:
        # TODO: remove this adapter when all callers create AuditLogEntry directly.
        self._conn.execute(
            """
            INSERT INTO audit_logs (timestamp, tool_name, risk_level, request_summary, result_status, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                tool_name,
                risk_level,
                request_summary,
                result_status,
                detail,
            ),
        )
        self._conn.commit()
