from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class RiskLevel(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    CONFIRMATION_REQUIRED = "confirmation_required"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass(frozen=True)
class ToolResult:
    status: ExecutionStatus
    message: str
    data: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ToolIntent:
    tool_name: str
    summary: str


@dataclass(frozen=True)
class AuditLogEntry:
    timestamp: datetime
    tool_name: str
    risk_level: RiskLevel
    request_summary: str
    result_status: ExecutionStatus
    detail: str
