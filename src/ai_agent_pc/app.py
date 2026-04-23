"""Minimal runnable app shell."""

import logging

from ai_agent_pc.config import load_config
from ai_agent_pc.db.sqlite import AuditLogger, SettingsRepository, initialize_sqlite
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator
from ai_agent_pc.routines.service import RoutineService
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry
from ai_agent_pc.ui.shell import UIShell
from ai_agent_pc.voice.service import VoiceService


class App:
    """Coordinates top-level components for local execution."""

    def __init__(self) -> None:
        self.config = load_config()
        initialize_sqlite(self.config.db_path)
        self._configure_logging()
        self.permissions = PermissionManager()
        self.monitoring = MonitoringService(
            db_path=self.config.db_path,
            config=self.config.monitoring,
        )
        self.tools = ToolRegistry(monitoring=self.monitoring)
        self.audit_logger = AuditLogger(self.config.db_path)
        self.settings = SettingsRepository(self.config.db_path)
        self.routines = RoutineService(
            db_path=self.config.db_path,
            tools=self.tools,
            permissions=self.permissions,
            audit=self.audit_logger,
        )
        self.orchestrator = AgentOrchestrator(
            permissions=self.permissions,
            tools=self.tools,
            monitoring=self.monitoring,
            routines=self.routines,
        )
        voice_settings = self.settings.get_json("voice", default={})
        self.voice = VoiceService()
        self.voice.settings.stt_enabled = bool(voice_settings.get("stt_enabled", self.voice.settings.stt_enabled))
        self.voice.settings.tts_enabled = bool(voice_settings.get("tts_enabled", self.voice.settings.tts_enabled))
        self.voice.settings.push_to_talk = bool(voice_settings.get("push_to_talk", self.voice.settings.push_to_talk))
        self.ui = UIShell(
            orchestrator=self.orchestrator,
            monitoring=self.monitoring,
            audit_logger=self.audit_logger,
            voice=self.voice,
            routines=self.routines,
            settings=self.settings,
        )

    def run(self) -> None:
        self.monitoring.log("app_started", {"db_path": str(self.config.db_path), "mode": "offline"})
        self.monitoring.start()
        try:
            self.ui.render_welcome()
        except KeyboardInterrupt:
            logging.getLogger(__name__).info("Application interrupted by user.")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.monitoring.stop()
        self.settings.set_json(
            "voice",
            {
                "stt_enabled": self.voice.settings.stt_enabled,
                "tts_enabled": self.voice.settings.tts_enabled,
                "push_to_talk": self.voice.settings.push_to_talk,
            },
        )
        self.monitoring.log("app_stopped", {"mode": "offline"})

    def _configure_logging(self) -> None:
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.FileHandler(self.config.log_path, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )


def create_app() -> App:
    return App()
