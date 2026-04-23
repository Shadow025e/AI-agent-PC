"""Minimal runnable app shell."""

from ai_agent_pc.config import load_config
from ai_agent_pc.db.sqlite import initialize_sqlite
from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry
from ai_agent_pc.ui.shell import UIShell


class App:
    """Coordinates top-level components for local execution."""

    def __init__(self) -> None:
        self.config = load_config()
        self.permissions = PermissionManager()
        self.monitoring = MonitoringService(
            db_path=self.config.db_path,
            config=self.config.monitoring,
        )
        self.tools = ToolRegistry()
        self.orchestrator = AgentOrchestrator(
            permissions=self.permissions,
            tools=self.tools,
            monitoring=self.monitoring,
        )
        self.ui = UIShell(orchestrator=self.orchestrator)

    def run(self) -> None:
        initialize_sqlite(self.config.db_path)
        self.monitoring.log("app_started", {"db_path": str(self.config.db_path)})
        self.ui.render_welcome()


def create_app() -> App:
    return App()
