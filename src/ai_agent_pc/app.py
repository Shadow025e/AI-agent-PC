"""Minimal runnable app shell."""

from ai_agent_pc.config import load_config
from ai_agent_pc.db.sqlite import AuditLogger, initialize_sqlite
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
        self.permissions = PermissionManager()
        self.monitoring = MonitoringService(
            db_path=self.config.db_path,
            config=self.config.monitoring,
        )
        self.tools = ToolRegistry(monitoring=self.monitoring)
        self.audit_logger = AuditLogger(self.config.db_path)
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
        self.voice = VoiceService()
        self.ui = UIShell(
            orchestrator=self.orchestrator,
            monitoring=self.monitoring,
            audit_logger=self.audit_logger,
            voice=self.voice,
            routines=self.routines,
        )

    def run(self) -> None:
        self.monitoring.log("app_started", {"db_path": str(self.config.db_path), "mode": "offline"})
        self.ui.render_welcome()


def create_app() -> App:
    return App()
