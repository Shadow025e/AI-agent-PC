from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass

from app.audit import AuditLogger
from app.db import init_database
from app.models import ExecutionStatus, RiskLevel, ToolResult
from app.orchestrator import AgentOrchestrator
from app.security import PermissionEvaluator
from app.tools.base import Tool, ToolContext
from app.tools.registry import ToolRegistry
from app.tools.system_tools import GetSystemInfoTool, ListProcessesTool


@dataclass
class HighRiskNoopTool(Tool):
    name: str = "dangerous_thing"
    description: str = "A high-risk placeholder tool for policy tests."
    risk_level: RiskLevel = RiskLevel.HIGH

    def execute(self, context: ToolContext) -> ToolResult:
        return ToolResult(status=ExecutionStatus.SUCCESS, message="Executed")


class BackendFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = f"{self.tmpdir.name}/agent.sqlite"
        self.conn = init_database(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmpdir.cleanup()

    def _build_orchestrator(self, registry: ToolRegistry) -> AgentOrchestrator:
        return AgentOrchestrator(
            registry=registry,
            permission_evaluator=PermissionEvaluator(allow_high_risk=False),
            audit_logger=AuditLogger(self.conn),
        )

    def test_tool_registration(self) -> None:
        registry = ToolRegistry()
        registry.register(GetSystemInfoTool())
        self.assertIn("get_system_info", registry.list_tools())

    def test_safe_action_execution(self) -> None:
        registry = ToolRegistry()
        registry.register(GetSystemInfoTool())
        orchestrator = self._build_orchestrator(registry)

        result = orchestrator.handle_request("show system info")

        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertIsNotNone(result.data)
        self.assertIn("platform", result.data or {})

    def test_medium_risk_handling(self) -> None:
        registry = ToolRegistry()
        registry.register(ListProcessesTool())
        orchestrator = self._build_orchestrator(registry)

        result = orchestrator.handle_request("list processes")

        self.assertEqual(result.status, ExecutionStatus.CONFIRMATION_REQUIRED)

    def test_high_risk_handling(self) -> None:
        registry = ToolRegistry()
        registry.register(HighRiskNoopTool())
        orchestrator = self._build_orchestrator(registry)

        result = orchestrator.handle_request("dangerous thing")

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)

    def test_unknown_tool_rejection(self) -> None:
        registry = ToolRegistry()
        orchestrator = self._build_orchestrator(registry)

        result = orchestrator.handle_request("nonexistent action")

        self.assertEqual(result.status, ExecutionStatus.REJECTED)

    def test_audit_log_creation(self) -> None:
        registry = ToolRegistry()
        registry.register(GetSystemInfoTool())
        orchestrator = self._build_orchestrator(registry)

        orchestrator.handle_request("show system info")

        row = self.conn.execute(
            "SELECT tool_name, risk_level, request_summary, result_status FROM audit_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row[0], "get_system_info")
        self.assertEqual(row[1], "safe")
        self.assertEqual(row[3], "success")


if __name__ == "__main__":
    unittest.main()
