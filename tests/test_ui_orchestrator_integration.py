from pathlib import Path

from ai_agent_pc.config import MonitoringConfig
from ai_agent_pc.db.sqlite import AuditLogger
from ai_agent_pc.monitoring.models import ProcessUsage, SystemSnapshot
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry


class StubCollector:
    def snapshot(self):
        return SystemSnapshot(cpu_percent=22, ram_percent=33, disk_percent=44, battery_percent=None, battery_status=None)

    def top_processes(self, limit: int = 5):
        return [ProcessUsage(pid=1, name="proc", cpu_percent=11, ram_percent=1.5)][:limit]

    def startup_entries(self):
        return []

    def recent_crash_count(self, window_seconds: int = 3600):
        return 0


def _make_orchestrator(tmp_path: Path) -> tuple[AgentOrchestrator, MonitoringService, AuditLogger]:
    db_path = tmp_path / "agent.db"
    monitoring = MonitoringService(
        db_path=db_path,
        config=MonitoringConfig(),
        collector=StubCollector(),
    )
    orchestrator = AgentOrchestrator(
        permissions=PermissionManager(),
        tools=ToolRegistry(),
        monitoring=monitoring,
    )
    return orchestrator, monitoring, AuditLogger(db_path)


def test_chat_request_routes_to_orchestrator_and_returns_structured_data(tmp_path: Path) -> None:
    orchestrator, _, _ = _make_orchestrator(tmp_path)

    response = orchestrator.handle_request("show system status")

    assert response.status == "ok"
    assert response.data is not None
    assert "system_status" in response.data


def test_medium_risk_requires_confirmation_then_executes(tmp_path: Path) -> None:
    orchestrator, _, _ = _make_orchestrator(tmp_path)

    response = orchestrator.handle_request("list processes")
    assert response.status == "confirmation_required"
    assert response.action_id is not None

    confirmed = orchestrator.confirm_action(response.action_id, approved=True)
    assert confirmed.status == "ok"
    assert confirmed.data is not None
    assert "processes" in confirmed.data


def test_high_risk_is_blocked_with_clear_message(tmp_path: Path) -> None:
    orchestrator, _, _ = _make_orchestrator(tmp_path)

    response = orchestrator.handle_request("delete all files")

    assert response.status == "blocked"
    assert "blocked" in response.message.lower()


def test_alerts_and_history_load_from_data_layer(tmp_path: Path) -> None:
    orchestrator, monitoring, audit = _make_orchestrator(tmp_path)

    monitoring.check_once()
    orchestrator.handle_request("show alerts")

    alerts = monitoring.list_alerts(limit=10)
    history = audit.list_events(limit=20)

    assert isinstance(alerts, list)
    assert isinstance(history, list)
    assert any(event["event"] in {"action_executed", "action_confirmation_required"} for event in history)
