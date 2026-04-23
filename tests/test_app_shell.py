from pathlib import Path

from ai_agent_pc.app import App, create_app
from ai_agent_pc.config import AppConfig, MonitoringConfig


def _patch_temp_config(monkeypatch, tmp_path: Path) -> None:
    config = AppConfig(
        project_root=tmp_path,
        data_dir=tmp_path / ".data",
        db_path=tmp_path / ".data" / "agent.db",
        log_path=tmp_path / ".data" / "app.log",
        monitoring=MonitoringConfig(polling_interval_seconds=0.05),
    )
    monkeypatch.setattr("ai_agent_pc.app.load_config", lambda: config)


def test_create_app_initializes_components(monkeypatch, tmp_path: Path) -> None:
    _patch_temp_config(monkeypatch, tmp_path)
    app = create_app()

    assert app.orchestrator is not None
    assert "get_system_status" in app.tools.list_tools()


def test_app_run_starts_and_stops_monitoring(monkeypatch, tmp_path: Path) -> None:
    _patch_temp_config(monkeypatch, tmp_path)
    app = App()
    monkeypatch.setattr(app.ui, "render_welcome", lambda: None)

    app.run()

    assert app.monitoring.is_running is False
    events = app.audit_logger.list_events(limit=20)
    names = [event["event"] for event in events]
    assert "app_started" in names
    assert "monitoring_started" in names
    assert "monitoring_stopped" in names
    assert "app_stopped" in names
