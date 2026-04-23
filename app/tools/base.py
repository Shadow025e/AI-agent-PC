from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import RiskLevel, ToolResult


@dataclass(frozen=True)
class ToolContext:
    request_text: str


class Tool(ABC):
    name: str
    description: str
    risk_level: RiskLevel

    @abstractmethod
    def execute(self, context: ToolContext) -> ToolResult:
        raise NotImplementedError
