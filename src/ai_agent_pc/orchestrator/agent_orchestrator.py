"""Agent orchestration boundary."""

from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.security.permissions import PermissionManager
from ai_agent_pc.tools.registry import ToolRegistry


class AgentOrchestrator:
    """Coordinates routines, tools, and policy checks.

    TODO: Implement task planning/execution loop with guarded tool invocation.
    """

    def __init__(
        self,
        permissions: PermissionManager,
        tools: ToolRegistry,
        monitoring: MonitoringService,
    ) -> None:
        self.permissions = permissions
        self.tools = tools
        self.monitoring = monitoring
