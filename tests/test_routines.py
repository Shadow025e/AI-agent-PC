from pathlib import Path

from ai_agent_pc.config import MonitoringConfig
import sqlite3

from ai_agent_pc.db.sqlite import AuditLogger, TrustedTargetRepository, initialize_sqlite
from ai_agent_pc.monitoring.models import ProcessUsage, SystemSnapshot
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.routines.service import RoutineService
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry


class StubCollector:
    def snapshot(self):
        return SystemSnapshot(cpu_percent=21, ram_percent=45, disk_percent=33, battery_percent=None, battery_status=None)

    def top_processes(self, limit: int = 5):
        return [ProcessUsage(pid=10, name="editor", cpu_percent=15, ram_percent=2.1)][:limit]

    def startup_entries(self):
        return []

    def recent_crash_count(self, window_seconds: int = 3600):
        return 0


def _make_service(tmp_path: Path, allow_high_risk: bool = False) -> tuple[RoutineService, AuditLogger, Path]:
    db_path = tmp_path / "agent.db"
    initialize_sqlite(db_path)
    monitoring = MonitoringService(db_path=db_path, config=MonitoringConfig(), collector=StubCollector())
    tools = ToolRegistry(monitoring=monitoring)
    audit = AuditLogger(db_path)
    service = RoutineService(db_path=db_path, tools=tools, permissions=PermissionManager(allow_high_risk=allow_high_risk), audit=audit)
    return service, audit, db_path


def test_seeded_routines_exist(tmp_path: Path) -> None:
    service, _, _ = _make_service(tmp_path)

    names = {r.name for r in service.list_routines()}

    assert names == {"Study Mode", "Coding Mode", "Low Resource Mode"}


def test_routine_validation_rejects_untrusted_targets(tmp_path: Path) -> None:
    service, _, _ = _make_service(tmp_path)

    error = service.validate_step("open_trusted_app", {"app": "malware_app"})

    assert error is not None
    assert "not allowlisted" in error


def test_safe_routine_execution_runs_through_registry(tmp_path: Path) -> None:
    service, _, _ = _make_service(tmp_path)

    result = service.run_routine("Study Mode", confirm_medium=True)

    assert result.status == "ok"
    assert any(step.tool_name == "get_system_status" for step in result.steps)


def test_confirmation_required_for_medium_risk_steps(tmp_path: Path) -> None:
    service, _, _ = _make_service(tmp_path)

    result = service.run_routine("Coding Mode", confirm_medium=False)

    assert result.status == "confirmation_required"
    assert result.steps[-1].requires_confirmation is True


def test_high_risk_steps_blocked_by_default(tmp_path: Path) -> None:
    service, _, db_path = _make_service(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO routines(name, description, built_in) VALUES(?, ?, 0)", ("Danger Mode", "High risk test",))
        routine_id = conn.execute("SELECT id FROM routines WHERE name = 'Danger Mode'").fetchone()[0]
        conn.execute(
            "INSERT INTO routine_steps(routine_id, step_order, tool_name, args_json) VALUES(?, 1, 'high_risk_placeholder', '{}')",
            (routine_id,),
        )
        conn.commit()

    result = service.run_routine("Danger Mode", confirm_medium=True)
    assert result.status == "blocked"


def test_routine_execution_logs_audit_steps(tmp_path: Path) -> None:
    service, audit, _ = _make_service(tmp_path)

    service.run_routine("Low Resource Mode", confirm_medium=True)
    events = audit.list_events(limit=30)

    assert any(event["event"] == "routine_started" for event in events)
    assert any(event["event"] == "routine_step" for event in events)


def test_trusted_path_validation(tmp_path: Path) -> None:
    service, _, db_path = _make_service(tmp_path)
    trusted = TrustedTargetRepository(db_path)
    trusted_path = trusted.list_trusted_paths()[0]

    assert service.validate_step("open_trusted_folder", {"path": trusted_path}) is None
    assert service.validate_step("open_trusted_folder", {"path": "/etc"}) is not None
