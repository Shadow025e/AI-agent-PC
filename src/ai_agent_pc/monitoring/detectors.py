"""Monitoring detectors that convert observations into alerts."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from ai_agent_pc.config import MonitoringConfig
from ai_agent_pc.monitoring.models import Alert, AlertLevel, ProcessUsage, SystemSnapshot


class ResourceDetector:
    """Rule-based local heuristics for resource and behavior anomalies."""

    def __init__(self, config: MonitoringConfig) -> None:
        self.config = config
        self._previous_snapshot: SystemSnapshot | None = None
        self._high_usage_events: deque[datetime] = deque()

    def evaluate(
        self,
        snapshot: SystemSnapshot | None,
        processes: list[ProcessUsage],
        startup_entries: list[str],
        recent_crash_count: int | None,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        now = datetime.now(timezone.utc)

        if snapshot is not None:
            alerts.extend(self._threshold_alerts(snapshot))
            alerts.extend(self._spike_alerts(snapshot))
            self._track_repeated_high_usage(snapshot, now)
        if len(self._high_usage_events) >= self.config.repeated_high_count:
            alerts.append(
                Alert(
                    level=AlertLevel.WARNING,
                    category="repeated_high_usage",
                    message="Repeated high CPU/RAM usage pattern detected.",
                    fingerprint="repeated-high-usage",
                    details={
                        "event_count": len(self._high_usage_events),
                        "window_seconds": self.config.repeated_high_window_seconds,
                    },
                )
            )

        alerts.extend(self._process_alerts(processes))
        alerts.extend(self._startup_alerts(startup_entries))
        alerts.extend(self._crash_alerts(recent_crash_count))
        self._previous_snapshot = snapshot
        return alerts

    def _threshold_alerts(self, snapshot: SystemSnapshot) -> list[Alert]:
        alerts: list[Alert] = []
        if snapshot.cpu_percent is not None and snapshot.cpu_percent >= self.config.high_cpu_percent:
            alerts.append(
                Alert(
                    level=AlertLevel.WARNING,
                    category="cpu_threshold",
                    message="CPU usage exceeded configured threshold.",
                    fingerprint="high-cpu-threshold",
                    details={"cpu_percent": snapshot.cpu_percent},
                )
            )
        if snapshot.ram_percent is not None and snapshot.ram_percent >= self.config.high_ram_percent:
            alerts.append(
                Alert(
                    level=AlertLevel.WARNING,
                    category="ram_threshold",
                    message="RAM usage exceeded configured threshold.",
                    fingerprint="high-ram-threshold",
                    details={"ram_percent": snapshot.ram_percent},
                )
            )
        if snapshot.disk_percent is not None and snapshot.disk_percent >= self.config.high_disk_percent:
            alerts.append(
                Alert(
                    level=AlertLevel.INFO,
                    category="disk_threshold",
                    message="Disk usage is approaching capacity.",
                    fingerprint="high-disk-threshold",
                    details={"disk_percent": snapshot.disk_percent},
                )
            )
        return alerts

    def _spike_alerts(self, snapshot: SystemSnapshot) -> list[Alert]:
        if self._previous_snapshot is None:
            return []
        alerts: list[Alert] = []
        alerts.extend(
            self._metric_spike(
                "cpu",
                self._previous_snapshot.cpu_percent,
                snapshot.cpu_percent,
                AlertLevel.CRITICAL,
            )
        )
        alerts.extend(
            self._metric_spike(
                "ram",
                self._previous_snapshot.ram_percent,
                snapshot.ram_percent,
                AlertLevel.WARNING,
            )
        )
        return alerts

    def _metric_spike(
        self,
        metric: str,
        previous: float | None,
        current: float | None,
        level: AlertLevel,
    ) -> list[Alert]:
        if previous is None or current is None:
            return []
        delta = current - previous
        if delta < self.config.spike_delta_percent:
            return []
        return [
            Alert(
                level=level,
                category=f"{metric}_spike",
                message=f"Abnormal {metric.upper()} usage spike detected.",
                fingerprint=f"{metric}-spike",
                details={"previous": previous, "current": current, "delta": delta},
            )
        ]

    def _process_alerts(self, processes: list[ProcessUsage]) -> list[Alert]:
        alerts: list[Alert] = []
        for process in processes:
            cpu_over = process.cpu_percent is not None and process.cpu_percent >= self.config.high_process_cpu_percent
            ram_over = process.ram_percent is not None and process.ram_percent >= self.config.high_process_ram_percent
            if not (cpu_over or ram_over):
                continue
            alerts.append(
                Alert(
                    level=AlertLevel.WARNING,
                    category="process_resource",
                    message=f"Process {process.name} (pid={process.pid}) is consuming excessive resources.",
                    fingerprint=f"process-resource-{process.pid}",
                    details={
                        "pid": process.pid,
                        "name": process.name,
                        "cpu_percent": process.cpu_percent,
                        "ram_percent": process.ram_percent,
                    },
                )
            )
        return alerts

    def _startup_alerts(self, startup_entries: list[str]) -> list[Alert]:
        suspicious_tokens = ("tmp", "powershell", "base64", "curl", "wget")
        hits = [
            entry
            for entry in startup_entries
            if any(token in entry.lower() for token in suspicious_tokens)
        ]
        if not hits:
            return []
        return [
            Alert(
                level=AlertLevel.INFO,
                category="startup_heuristic",
                message="Suspicious startup entries detected (heuristic placeholder).",
                fingerprint="suspicious-startup-entries",
                details={"matches": hits},
            )
        ]

    def _crash_alerts(self, recent_crash_count: int | None) -> list[Alert]:
        if recent_crash_count is None:
            return []
        if recent_crash_count < self.config.frequent_crash_threshold:
            return []
        return [
            Alert(
                level=AlertLevel.WARNING,
                category="frequent_crashes",
                message="Frequent crashes detected from local crash log signal.",
                fingerprint="frequent-crashes",
                details={"count": recent_crash_count},
            )
        ]

    def _track_repeated_high_usage(self, snapshot: SystemSnapshot, now: datetime) -> None:
        is_high = (
            snapshot.cpu_percent is not None
            and snapshot.cpu_percent >= self.config.high_cpu_percent
        ) or (
            snapshot.ram_percent is not None
            and snapshot.ram_percent >= self.config.high_ram_percent
        )
        if is_high:
            self._high_usage_events.append(now)

        window_start = now.timestamp() - self.config.repeated_high_window_seconds
        while self._high_usage_events and self._high_usage_events[0].timestamp() < window_start:
            self._high_usage_events.popleft()
