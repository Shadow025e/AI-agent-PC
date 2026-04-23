"""Console UI placeholder for local MVP."""

from ai_agent_pc.orchestrator.agent_orchestrator import AgentOrchestrator


class UIShell:
    """Minimal CLI shell placeholder.

    TODO: Replace with richer desktop/web UI boundary once interaction flow stabilizes.
    """

    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self.orchestrator = orchestrator

    def render_welcome(self) -> None:
        print("AI-agent-PC scaffold is running (local-only mode).")
