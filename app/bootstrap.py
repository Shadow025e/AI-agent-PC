from __future__ import annotations

from pathlib import Path

from app.audit import AuditLogger
from app.db import init_database
from app.orchestrator import AgentOrchestrator
from app.security import PermissionEvaluator
from app.tools.registry import ToolRegistry
from app.tools.system_tools import GetResourceUsageTool, GetSystemInfoTool, ListProcessesTool


def build_orchestrator(db_path: str | Path, *, allow_high_risk: bool = False) -> AgentOrchestrator:
    conn = init_database(db_path)
    registry = ToolRegistry()
    registry.register(GetSystemInfoTool())
    registry.register(GetResourceUsageTool())
    registry.register(ListProcessesTool())

    return AgentOrchestrator(
        registry=registry,
        permission_evaluator=PermissionEvaluator(allow_high_risk=allow_high_risk),
        audit_logger=AuditLogger(conn),
    )
