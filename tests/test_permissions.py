from ai_agent_pc.security.permissions import PermissionDecision, PermissionManager, RiskLevel


def test_permissions_default_deny_high_risk() -> None:
    perms = PermissionManager()
    assert perms.can_execute("any_action") is False


def test_permissions_require_confirmation_for_medium_risk() -> None:
    perms = PermissionManager()
    decision = perms.evaluate("list_processes", RiskLevel.MEDIUM)

    assert decision.decision is PermissionDecision.REQUIRE_CONFIRMATION
