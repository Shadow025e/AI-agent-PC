from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.models import ExecutionStatus, RiskLevel, ToolResult
from app.tools.base import Tool, ToolContext


@dataclass
class GetSystemInfoTool(Tool):
    name: str = "get_system_info"
    description: str = "Returns basic host OS and Python runtime information."
    risk_level: RiskLevel = RiskLevel.SAFE

    def execute(self, context: ToolContext) -> ToolResult:
        return ToolResult(
            status=ExecutionStatus.SUCCESS,
            message="System info collected.",
            data={
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
            },
        )


@dataclass
class GetResourceUsageTool(Tool):
    name: str = "get_resource_usage"
    description: str = "Returns basic CPU/load and disk usage information."
    risk_level: RiskLevel = RiskLevel.SAFE

    def execute(self, context: ToolContext) -> ToolResult:
        loadavg = None
        if hasattr(os, "getloadavg"):
            try:
                loadavg = os.getloadavg()
            except OSError:
                loadavg = None

        usage = shutil.disk_usage(Path.home())

        return ToolResult(
            status=ExecutionStatus.SUCCESS,
            message="Resource usage collected.",
            data={
                "loadavg": loadavg,
                "disk_total_bytes": usage.total,
                "disk_used_bytes": usage.used,
                "disk_free_bytes": usage.free,
            },
        )


@dataclass
class ListProcessesTool(Tool):
    name: str = "list_processes"
    description: str = "Lists visible process IDs and command names from /proc."
    risk_level: RiskLevel = RiskLevel.MEDIUM

    def execute(self, context: ToolContext) -> ToolResult:
        processes: list[dict[str, str | int]] = []
        proc = Path("/proc")
        if not proc.exists():
            return ToolResult(
                status=ExecutionStatus.ERROR,
                message="/proc is unavailable on this system.",
            )

        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            comm_file = entry / "comm"
            try:
                name = comm_file.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                name = "<unknown>"
            processes.append({"pid": int(entry.name), "name": name})

        processes.sort(key=lambda item: int(item["pid"]))
        return ToolResult(
            status=ExecutionStatus.SUCCESS,
            message="Process list collected.",
            data={"processes": processes[:200]},
        )
