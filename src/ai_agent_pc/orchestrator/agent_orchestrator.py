"""Agent orchestration boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.routines.service import RoutineService
from ai_agent_pc.security.permissions import PermissionDecision, PermissionManager, RiskLevel
from ai_agent_pc.tools.registry import ToolRegistry


@dataclass
class AgentResponse:
    status: str
    message: str
    data: dict[str, object] | None = None
    action_id: str | None = None
    action: str | None = None


class AgentOrchestrator:
    """Coordinates routines, tools, and policy checks for local UI flows."""

    def __init__(
        self,
        permissions: PermissionManager,
        tools: ToolRegistry,
        monitoring: MonitoringService,
        routines: RoutineService | None = None,
    ) -> None:
        self.permissions = permissions
        self.tools = tools
        self.monitoring = monitoring
        self.routines = routines
        self._pending_actions: dict[str, tuple[str, RiskLevel]] = {}

    def handle_request(self, request_text: str) -> AgentResponse:
        action, risk = self._classify_request(request_text)
        decision = self.permissions.evaluate(action, risk)

        if decision.decision is PermissionDecision.BLOCK:
            self.monitoring.log(
                "action_blocked",
                {"request": request_text, "action": action, "risk": risk.value, "reason": decision.reason},
            )
            return AgentResponse(status="blocked", message=decision.reason, data={"risk": risk.value, "action": action})

        if decision.decision is PermissionDecision.REQUIRE_CONFIRMATION:
            action_id = self._new_action_id(action)
            self._pending_actions[action_id] = (action, risk)
            self.monitoring.log(
                "action_confirmation_required",
                {"request": request_text, "action": action, "risk": risk.value, "action_id": action_id},
            )
            return AgentResponse(
                status="confirmation_required",
                message=f"Confirm '{action}' before execution.",
                data={"risk": risk.value, "action": action},
                action_id=action_id,
                action=action,
            )

        result = self._execute_action(action)
        self.monitoring.log(
            "action_executed",
            {"request": request_text, "action": action, "risk": risk.value, "result_status": result.status},
        )
        return result

    def confirm_action(self, action_id: str, approved: bool) -> AgentResponse:
        pending = self._pending_actions.pop(action_id, None)
        if pending is None:
            return AgentResponse(status="error", message="No pending action found for confirmation.")

        action, risk = pending
        if not approved:
            self.monitoring.log(
                "action_confirmation_declined",
                {"action": action, "risk": risk.value, "action_id": action_id},
            )
            return AgentResponse(status="cancelled", message=f"Action '{action}' cancelled.")

        result = self._execute_action(action)
        self.monitoring.log(
            "action_confirmed_and_executed",
            {"action": action, "risk": risk.value, "action_id": action_id, "result_status": result.status},
        )
        return result

    def execute_routine(self, name: str, confirm_medium: bool = False) -> AgentResponse:
        if self.routines is None:
            return AgentResponse(status="error", message="Routine service is not configured.")
        result = self.routines.run_routine(name=name, confirm_medium=confirm_medium)
        return AgentResponse(
            status=result.status,
            message=result.message,
            data={"routine": result.routine_name, "steps": [step.__dict__ for step in result.steps]},
            action=f"routine:{name}",
        )

    def _execute_action(self, action: str) -> AgentResponse:
        tool = self.tools.get(action)
        if tool is not None:
            spec, handler = tool
            result = handler({})
            return AgentResponse(status=result.status, message=result.message, data=result.data, action=spec.name)
        return AgentResponse(status="ok", message="Request recorded. No matching action executed.", data={"echo": action})

    def _classify_request(self, text: str) -> tuple[str, RiskLevel]:
        query = text.strip().lower()
        if any(token in query for token in ("shutdown", "delete", "wipe", "format", "disable security")):
            return "high_risk_action", RiskLevel.HIGH
        if "process" in query:
            return "list_processes", RiskLevel.MEDIUM
        if "alert" in query:
            return "list_alerts", RiskLevel.SAFE
        if any(token in query for token in ("status", "health", "system")):
            return "get_system_status", RiskLevel.SAFE
        return "general_assistance", RiskLevel.SAFE

    @staticmethod
    def _new_action_id(action: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"{action}-{timestamp}"


def build_routine_service(db_path: Path, tools: ToolRegistry, permissions: PermissionManager, monitoring: MonitoringService) -> RoutineService:
    from ai_agent_pc.db.sqlite import AuditLogger

    return RoutineService(db_path=db_path, tools=tools, permissions=permissions, audit=AuditLogger(db_path))
