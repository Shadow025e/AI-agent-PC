"""Permission model for local offline actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    BLOCK = "block"


@dataclass(frozen=True)
class PermissionResult:
    decision: PermissionDecision
    reason: str


class PermissionManager:
    """Enforces local security boundaries with explicit risk decisions."""

    def __init__(self, allow_high_risk: bool = False) -> None:
        self.allow_high_risk = allow_high_risk

    def evaluate(self, action: str, risk: RiskLevel) -> PermissionResult:
        if risk is RiskLevel.SAFE:
            return PermissionResult(PermissionDecision.ALLOW, "Safe action allowed.")
        if risk is RiskLevel.MEDIUM:
            return PermissionResult(
                PermissionDecision.REQUIRE_CONFIRMATION,
                f"Action '{action}' requires user confirmation.",
            )
        if self.allow_high_risk:
            return PermissionResult(
                PermissionDecision.REQUIRE_CONFIRMATION,
                f"High-risk action '{action}' is enabled but needs confirmation.",
            )
        return PermissionResult(
            PermissionDecision.BLOCK,
            f"Action '{action}' is blocked by high-risk policy.",
        )

    def can_execute(self, action: str) -> bool:
        """Backwards-compatible API used by earlier tests."""

        return self.evaluate(action, RiskLevel.HIGH).decision is PermissionDecision.ALLOW
