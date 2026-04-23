from __future__ import annotations

from dataclasses import dataclass

from app.models import ExecutionStatus, RiskLevel, ToolResult


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    requires_confirmation: bool
    result: ToolResult | None = None


class PermissionEvaluator:
    def __init__(self, allow_high_risk: bool = False) -> None:
        self.allow_high_risk = allow_high_risk

    def evaluate(self, risk_level: RiskLevel) -> PermissionDecision:
        if risk_level == RiskLevel.SAFE:
            return PermissionDecision(allowed=True, requires_confirmation=False)

        if risk_level == RiskLevel.MEDIUM:
            return PermissionDecision(
                allowed=False,
                requires_confirmation=True,
                result=ToolResult(
                    status=ExecutionStatus.CONFIRMATION_REQUIRED,
                    message="Action requires explicit confirmation before execution.",
                ),
            )

        if risk_level == RiskLevel.HIGH and not self.allow_high_risk:
            return PermissionDecision(
                allowed=False,
                requires_confirmation=False,
                result=ToolResult(
                    status=ExecutionStatus.BLOCKED,
                    message="High-risk action is blocked by default policy.",
                ),
            )

        return PermissionDecision(allowed=True, requires_confirmation=False)
