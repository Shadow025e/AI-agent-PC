from pathlib import Path

from ai_agent_pc.config import MonitoringConfig
from ai_agent_pc.monitoring.detectors import ResourceDetector
from ai_agent_pc.monitoring.models import ProcessUsage, SystemSnapshot
from ai_agent_pc.monitoring.service import MonitoringService


class StubCollector:
    def __init__(self, snapshots, processes=None, startups=None, crashes=0):
        self._snapshots = list(snapshots)
        self._index = 0
        self._processes = processes or []
        self._startups = startups or []
        self._crashes = crashes

    def snapshot(self):
        value = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return value

    def top_processes(self, limit: int = 5):
        return self._processes[:limit]

    def startup_entries(self):
        return self._startups

    def recent_crash_count(self, window_seconds: int = 3600):
        return self._crashes


def test_threshold_triggering() -> None:
    detector = ResourceDetector(
        MonitoringConfig(
            high_cpu_percent=80,
            high_ram_percent=70,
            high_disk_percent=90,
        )
    )
    snapshot = SystemSnapshot(cpu_percent=95, ram_percent=88, disk_percent=91, battery_percent=None, battery_status=None)
    alerts = detector.evaluate(snapshot, [], [], 0)

    categories = {alert.category for alert in alerts}
    assert "cpu_threshold" in categories
    assert "ram_threshold" in categories
    assert "disk_threshold" in categories


def test_alert_creation_and_query(tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    collector = StubCollector(
        snapshots=[SystemSnapshot(cpu_percent=96, ram_percent=15, disk_percent=20, battery_percent=None, battery_status=None)],
        processes=[ProcessUsage(pid=123, name="hog", cpu_percent=95, ram_percent=10)],
    )
    service = MonitoringService(
        db_path=db_path,
        config=MonitoringConfig(high_cpu_percent=80, high_process_cpu_percent=90, dedup_window_seconds=300),
        collector=collector,
    )

    service.check_once()
    alerts = service.list_alerts()

    assert len(alerts) >= 2
    assert any(alert["category"] == "cpu_threshold" for alert in alerts)
    assert any(alert["category"] == "process_resource" for alert in alerts)


def test_alert_deduplication(tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    snapshot = SystemSnapshot(cpu_percent=99, ram_percent=10, disk_percent=10, battery_percent=None, battery_status=None)
    collector = StubCollector([snapshot, snapshot])
    service = MonitoringService(
        db_path=db_path,
        config=MonitoringConfig(high_cpu_percent=80, dedup_window_seconds=600),
        collector=collector,
    )

    service.check_once()
    service.check_once()
    alerts = [a for a in service.list_alerts() if a["category"] == "cpu_threshold"]

    assert len(alerts) == 1
    assert alerts[0]["occurrence_count"] == 2


def test_safe_behavior_when_system_info_unavailable(tmp_path: Path) -> None:
    db_path = tmp_path / "agent.db"
    collector = StubCollector(snapshots=[None], crashes=None)
    service = MonitoringService(db_path=db_path, collector=collector)

    service.check_once()
    assert service.list_alerts() == []
