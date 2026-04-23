"""Monitoring service placeholders."""


class MonitoringService:
    """Collects local logs/metrics.

    TODO: Persist events to SQLite and provide observability dashboard feed.
    """

    def log(self, event: str, payload: dict[str, str]) -> None:
        print(f"[monitoring] {event}: {payload}")
