from ai_agent_pc.security.permissions import PermissionManager


def test_permissions_default_deny() -> None:
    perms = PermissionManager()
    assert perms.can_execute("any_action") is False
