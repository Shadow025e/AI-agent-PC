from pathlib import Path

from ai_agent_pc.app import App
from ai_agent_pc.config import AppConfig, MonitoringConfig
from ai_agent_pc.db.sqlite import SettingsRepository


def _app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        project_root=tmp_path,
        data_dir=tmp_path / ".data",
        db_path=tmp_path / ".data" / "agent.db",
        log_path=tmp_path / ".data" / "app.log",
        monitoring=MonitoringConfig(polling_interval_seconds=0.05),
    )


def test_settings_repository_round_trip(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "agent.db")
    repo.set_json("voice", {"stt_enabled": True, "tts_enabled": False, "push_to_talk": True})

    payload = repo.get_json("voice")

    assert payload["stt_enabled"] is True
    assert payload["tts_enabled"] is False
    assert payload["push_to_talk"] is True


def test_voice_settings_persist_across_app_instances(monkeypatch, tmp_path: Path) -> None:
    config = _app_config(tmp_path)
    monkeypatch.setattr("ai_agent_pc.app.load_config", lambda: config)

    app1 = App()
    app1.voice.settings.stt_enabled = False
    app1.voice.settings.tts_enabled = True
    app1.voice.settings.push_to_talk = False
    app1.shutdown()

    app2 = App()

    assert app2.voice.settings.stt_enabled is False
    assert app2.voice.settings.tts_enabled is True
    assert app2.voice.settings.push_to_talk is False
