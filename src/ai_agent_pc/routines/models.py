"""Routine model layer for local workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_agent_pc.security.permissions import RiskLevel


@dataclass
class RoutineStep:
    id: int
    tool_name: str
    args: dict[str, object] = field(default_factory=dict)


@dataclass
class Routine:
    id: int
    name: str
    description: str
    built_in: bool
    steps: list[RoutineStep] = field(default_factory=list)


@dataclass
class RoutineStepResult:
    routine_name: str
    step_id: int
    tool_name: str
    risk: RiskLevel
    status: str
    message: str
    requires_confirmation: bool = False
    blocked: bool = False
    data: dict[str, object] | None = None


@dataclass
class RoutineExecutionResult:
    routine_name: str
    status: str
    steps: list[RoutineStepResult]
    message: str
