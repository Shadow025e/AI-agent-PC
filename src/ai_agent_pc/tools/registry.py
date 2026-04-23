"""Tool registry placeholders."""


class ToolRegistry:
    """Central index of local tools.

    TODO: Add tool contracts, metadata, and safe invocation wrappers.
    """

    def __init__(self) -> None:
        self._tools: dict[str, object] = {}

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())
