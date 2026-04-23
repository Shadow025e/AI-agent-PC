"""Monitoring service for local system health and heuristic alerts."""

from __future__ import annotations

from pathlib import Path
import threading

from ai_agent_pc.config import MonitoringConfig
from ai_agent_pc.db.sqlite import AlertRepository, AuditLogger
from ai_agent_pc.monitoring.collectors import LocalSystemInfoCollector
from ai_agent_pc.monitoring.detectors import ResourceDetector


class MonitoringService:
    """Local monitoring lifecycle with start/stop and alert persistence."""

    def __init__(
        self,
        db_path: Path | None = None,
        config: MonitoringConfig | None = None,
        collector: LocalSystemInfoCollector | None = None,
        detector: ResourceDetector | None = None,
    ) -> None:
        self._config = config or MonitoringConfig()
        self._collector = collector or LocalSystemInfoCollector()
        self._detector = detector or ResourceDetector(self._config)
        self._db_path = db_path or Path.cwd() / ".data/agent.db"
        self._alerts = AlertRepository(self._db_path)
        self._audit = AuditLogger(self._db_path)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="monitoring-service", daemon=True)
        self._thread.start()
        self.log("monitoring_started", {"polling_interval_seconds": self._config.polling_interval_seconds})

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        assert self._thread is not None
        self._thread.join(timeout=max(1.0, self._config.polling_interval_seconds + 1.0))
        self.log("monitoring_stopped", {})

    def check_once(self) -> None:
        snapshot = self._collector.snapshot()
        processes = self._collector.top_processes()
        startup_entries = self._collector.startup_entries()
        recent_crashes = self._collector.recent_crash_count(
            window_seconds=self._config.repeated_high_window_seconds
        )
        alerts = self._detector.evaluate(snapshot, processes, startup_entries, recent_crashes)

        for alert in alerts:
            inserted = self._alerts.store_alert(alert, dedup_window_seconds=self._config.dedup_window_seconds)
            event_name = "alert_created" if inserted else "alert_deduplicated"
            self.log(
                event_name,
                {
                    "level": alert.level.value,
                    "category": alert.category,
                    "fingerprint": alert.fingerprint,
                    "details": alert.details,
                },
            )

    def list_alerts(self, limit: int = 100) -> list[dict[str, object]]:
        return self._alerts.list_alerts(limit=limit)

    def current_system_status(self) -> dict[str, object]:
        snapshot = self._collector.snapshot()
        if snapshot is None:
            return {
                "cpu_percent": None,
                "ram_percent": None,
                "disk_percent": None,
                "battery_percent": None,
                "battery_status": None,
            }
        return {
            "cpu_percent": snapshot.cpu_percent,
            "ram_percent": snapshot.ram_percent,
            "disk_percent": snapshot.disk_percent,
            "battery_percent": snapshot.battery_percent,
            "battery_status": snapshot.battery_status,
        }

    def collector_top_processes(self, limit: int = 5):
        return self._collector.top_processes(limit=limit)

    def log(self, event: str, payload: dict[str, object]) -> None:
        self._audit.log(event, payload)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.check_once()
            self._stop_event.wait(self._config.polling_interval_seconds)
