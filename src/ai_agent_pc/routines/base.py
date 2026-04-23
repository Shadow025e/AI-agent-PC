"""Routine placeholders."""


class Routine:
    """Base routine contract.

    TODO: Define routine lifecycle and state contract.
    """

    name = "base"

    def run(self) -> None:
        raise NotImplementedError
