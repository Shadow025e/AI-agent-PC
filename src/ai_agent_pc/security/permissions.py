"""Permission model placeholders."""


class PermissionManager:
    """Enforces local security boundaries.

    TODO: Implement capability scopes and user consent workflow.
    """

    def can_execute(self, action: str) -> bool:
        # Secure-by-default for scaffold.
        return False
