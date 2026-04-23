"""Local tool registry with explicit metadata and safe execution wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ai_agent_pc.monitoring.service import MonitoringService
from ai_agent_pc.security.permissions import RiskLevel


@dataclass
class ToolSpec:
    """Registered local tool contract."""

    name: str
    risk: RiskLevel
    description: str
    requires_trusted_app: bool = False
    requires_trusted_path: bool = False


@dataclass
class ToolExecutionResult:
    status: str
    message: str
    data: dict[str, object] | None = None


ToolHandler = Callable[[dict[str, object]], ToolExecutionResult]


class ToolRegistry:
    """Central index of local tools with metadata + handlers."""

    def __init__(self, monitoring: MonitoringService | None = None) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolHandler]] = {}
        self._monitoring = monitoring
        self._register_builtin_tools()

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        self._tools[spec.name] = (spec, handler)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def get(self, name: str) -> tuple[ToolSpec, ToolHandler] | None:
        return self._tools.get(name)

    def _register_builtin_tools(self) -> None:
        self.register(
            ToolSpec(name="open_trusted_app", risk=RiskLevel.MEDIUM, description="Open an allowlisted local app.", requires_trusted_app=True),
            self._open_trusted_app,
        )
        self.register(
            ToolSpec(name="open_trusted_folder", risk=RiskLevel.SAFE, description="Open an allowlisted local folder.", requires_trusted_path=True),
            self._open_trusted_folder,
        )
        self.register(
            ToolSpec(name="get_system_status", risk=RiskLevel.SAFE, description="Read current local system status."),
            self._get_system_status,
        )
        self.register(
            ToolSpec(name="list_processes", risk=RiskLevel.MEDIUM, description="List top local processes."),
            self._list_processes,
        )
        self.register(
            ToolSpec(name="suggest_close_non_critical_apps", risk=RiskLevel.SAFE, description="Suggest candidate non-critical apps to close without force-closing."),
            self._suggest_close_non_critical_apps,
        )
        self.register(
            ToolSpec(name="high_risk_placeholder", risk=RiskLevel.HIGH, description="High-risk placeholder action for policy coverage."),
            self._high_risk_placeholder,
        )

    def _open_trusted_app(self, args: dict[str, object]) -> ToolExecutionResult:
        app = str(args.get("app", ""))
        return ToolExecutionResult(status="ok", message=f"Trusted app launch request accepted for '{app}'.", data={"app": app})

    def _open_trusted_folder(self, args: dict[str, object]) -> ToolExecutionResult:
        raw_path = str(args.get("path", ""))
        return ToolExecutionResult(
            status="ok",
            message=f"Trusted folder open request accepted for '{raw_path}'.",
            data={"path": str(Path(raw_path))},
        )

    def _get_system_status(self, _args: dict[str, object]) -> ToolExecutionResult:
        status = self._monitoring.current_system_status() if self._monitoring else {}
        return ToolExecutionResult(status="ok", message="System status fetched.", data={"system_status": status})

    def _list_processes(self, args: dict[str, object]) -> ToolExecutionResult:
        limit = int(args.get("limit", 10))
        processes = self._monitoring.collector_top_processes(limit=limit) if self._monitoring else []
        return ToolExecutionResult(
            status="ok",
            message="Top processes fetched.",
            data={"processes": [p.__dict__ for p in processes]},
        )

    def _suggest_close_non_critical_apps(self, _args: dict[str, object]) -> ToolExecutionResult:
        return ToolExecutionResult(
            status="ok",
            message="Close-app automation is not enabled in MVP; suggestion-only placeholder executed.",
            data={"todo": "Integrate close-app tool when implemented."},
        )

    def _high_risk_placeholder(self, _args: dict[str, object]) -> ToolExecutionResult:
        return ToolExecutionResult(status="ok", message="High risk placeholder executed.")
