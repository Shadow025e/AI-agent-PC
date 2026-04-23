"""Local system information collection (offline-only)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import time

from ai_agent_pc.monitoring.models import ProcessUsage, SystemSnapshot


@dataclass
class _CpuTimes:
    total: int
    idle: int


class LocalSystemInfoCollector:
    """Collects resource data from local OS primitives with safe fallbacks."""

    def __init__(self) -> None:
        self._last_cpu_times: _CpuTimes | None = None

    def snapshot(self) -> SystemSnapshot:
        return SystemSnapshot(
            cpu_percent=self._cpu_percent(),
            ram_percent=self._ram_percent(),
            disk_percent=self._disk_percent(),
            battery_percent=self._battery_percent(),
            battery_status=self._battery_status(),
        )

    def top_processes(self, limit: int = 5) -> list[ProcessUsage]:
        mem_total_kb = self._mem_total_kb()
        processes: list[ProcessUsage] = []
        proc_root = Path("/proc")
        if not proc_root.exists() or mem_total_kb is None or mem_total_kb <= 0:
            return processes

        for item in proc_root.iterdir():
            if not item.name.isdigit():
                continue
            pid = int(item.name)
            name = self._read_first_line(item / "comm") or f"pid-{pid}"
            rss_kb = self._read_rss_kb(item / "status")
            ram_pct = (rss_kb / mem_total_kb) * 100.0 if rss_kb is not None else None
            processes.append(ProcessUsage(pid=pid, name=name, cpu_percent=None, ram_percent=ram_pct))

        processes.sort(key=lambda proc: proc.ram_percent or 0.0, reverse=True)
        return processes[:limit]

    def startup_entries(self) -> list[str]:
        entries: list[str] = []
        for root in (Path.home() / ".config/autostart", Path("/etc/init.d")):
            if not root.exists():
                continue
            for path in root.iterdir():
                entries.append(path.name.lower())
        return entries

    def recent_crash_count(self, window_seconds: int = 3600) -> int | None:
        crash_log = Path.home() / ".local/share/ai-agent-pc/crash.log"
        if not crash_log.exists():
            return 0
        threshold = time.time() - window_seconds
        count = 0
        with crash_log.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    ts = float(line.strip().split(",", 1)[0])
                except (ValueError, IndexError):
                    continue
                if ts >= threshold:
                    count += 1
        return count

    def _cpu_percent(self) -> float | None:
        stat = self._read_first_line(Path("/proc/stat"))
        if not stat or not stat.startswith("cpu "):
            return None
        values = [int(v) for v in stat.split()[1:8]]
        idle = values[3] + values[4]
        total = sum(values)
        current = _CpuTimes(total=total, idle=idle)
        previous = self._last_cpu_times
        self._last_cpu_times = current

        if previous is None:
            return 0.0

        total_delta = current.total - previous.total
        idle_delta = current.idle - previous.idle
        if total_delta <= 0:
            return 0.0
        usage = (1.0 - (idle_delta / total_delta)) * 100.0
        return max(0.0, min(100.0, usage))

    def _ram_percent(self) -> float | None:
        meminfo = Path("/proc/meminfo")
        if not meminfo.exists():
            return None

        values: dict[str, int] = {}
        with meminfo.open("r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                value = parts[1].strip().split()[0]
                try:
                    values[key] = int(value)
                except ValueError:
                    continue
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return None
        used = total - available
        return (used / total) * 100.0

    def _disk_percent(self) -> float | None:
        try:
            usage = shutil.disk_usage("/")
        except OSError:
            return None
        if usage.total <= 0:
            return None
        return (usage.used / usage.total) * 100.0

    def _battery_percent(self) -> float | None:
        for battery_dir in Path("/sys/class/power_supply").glob("BAT*"):
            capacity = self._read_first_line(battery_dir / "capacity")
            if capacity is None:
                continue
            try:
                return float(capacity)
            except ValueError:
                return None
        return None

    def _battery_status(self) -> str | None:
        for battery_dir in Path("/sys/class/power_supply").glob("BAT*"):
            return self._read_first_line(battery_dir / "status")
        return None

    def _mem_total_kb(self) -> int | None:
        meminfo = Path("/proc/meminfo")
        if not meminfo.exists():
            return None
        with meminfo.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    try:
                        return int(line.split()[1])
                    except (ValueError, IndexError):
                        return None
        return None

    @staticmethod
    def _read_first_line(path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return handle.readline().strip()
        except OSError:
            return None

    @staticmethod
    def _read_rss_kb(status_path: Path) -> int | None:
        try:
            with status_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        try:
                            return int(line.split()[1])
                        except (IndexError, ValueError):
                            return None
        except OSError:
            return None
        return None
