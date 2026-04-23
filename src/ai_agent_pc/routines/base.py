"""Shared routine contracts."""


class Routine:
    """Base routine contract used by compatibility imports."""

    name = "base"

    def run(self) -> None:
        raise NotImplementedError
