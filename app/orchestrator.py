from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.audit import AuditLogger
from app.models import AuditLogEntry, ExecutionStatus, RiskLevel, ToolIntent, ToolResult
from app.security import PermissionEvaluator
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry


@dataclass
class AgentOrchestrator:
    registry: ToolRegistry
    permission_evaluator: PermissionEvaluator
    audit_logger: AuditLogger

    def handle_request(self, request_text: str) -> ToolResult:
        intent = self._map_to_intent(request_text)
        tool = self.registry.get(intent.tool_name)

        if tool is None:
            result = ToolResult(
                status=ExecutionStatus.REJECTED,
                message=f"Unknown tool intent: {intent.tool_name}",
            )
            self._audit(tool_name=intent.tool_name, risk_level=RiskLevel.HIGH, summary=intent.summary, result=result)
            return result

        decision = self.permission_evaluator.evaluate(tool.risk_level)
        if not decision.allowed:
            result = decision.result or ToolResult(
                status=ExecutionStatus.BLOCKED,
                message="Tool execution blocked by policy.",
            )
            self._audit(tool_name=tool.name, risk_level=tool.risk_level, summary=intent.summary, result=result)
            return result

        try:
            result = tool.execute(ToolContext(request_text=request_text))
        except Exception as exc:  # noqa: BLE001 - preserve predictable output
            result = ToolResult(status=ExecutionStatus.ERROR, message=f"Tool execution failed: {exc}")

        self._audit(tool_name=tool.name, risk_level=tool.risk_level, summary=intent.summary, result=result)
        return result

    def _map_to_intent(self, request_text: str) -> ToolIntent:
        lowered = request_text.strip().lower()
        if "system" in lowered or "os" in lowered:
            return ToolIntent(tool_name="get_system_info", summary=request_text[:160])
        if "resource" in lowered or "cpu" in lowered or "disk" in lowered:
            return ToolIntent(tool_name="get_resource_usage", summary=request_text[:160])
        if "process" in lowered:
            return ToolIntent(tool_name="list_processes", summary=request_text[:160])

        # TODO: replace with explicit parser/router once request schema is finalized.
        return ToolIntent(tool_name=lowered.replace(" ", "_"), summary=request_text[:160])

    def _audit(self, *, tool_name: str, risk_level: RiskLevel, summary: str, result: ToolResult) -> None:
        self.audit_logger.write(
            AuditLogEntry(
                timestamp=datetime.now(timezone.utc),
                tool_name=tool_name,
                risk_level=risk_level,
                request_summary=summary,
                result_status=result.status,
                detail=result.message,
            )
        )
