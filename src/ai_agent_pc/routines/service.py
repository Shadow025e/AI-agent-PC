"""Routine execution + validation service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_agent_pc.db.sqlite import AuditLogger, RoutineRepository, TrustedTargetRepository
from ai_agent_pc.routines.models import Routine, RoutineExecutionResult, RoutineStepResult
from ai_agent_pc.security.permissions import PermissionDecision, PermissionManager, RiskLevel
from ai_agent_pc.tools.registry import ToolRegistry


@dataclass
class TrustedValidationResult:
    ok: bool
    reason: str = ""


class RoutineService:
    """Executes DB-backed routines strictly through registered tools + permissions."""

    def __init__(
        self,
        db_path: Path,
        tools: ToolRegistry,
        permissions: PermissionManager,
        audit: AuditLogger,
    ) -> None:
        self._repo = RoutineRepository(db_path)
        self._trusted = TrustedTargetRepository(db_path)
        self._tools = tools
        self._permissions = permissions
        self._audit = audit

    def list_routines(self) -> list[Routine]:
        return self._repo.list_routines()

    def get_routine(self, name: str) -> Routine | None:
        return self._repo.get_routine(name)

    def run_routine(self, name: str, confirm_medium: bool = False) -> RoutineExecutionResult:
        routine = self._repo.get_routine(name)
        if routine is None:
            return RoutineExecutionResult(routine_name=name, status="error", steps=[], message="Routine not found.")

        results: list[RoutineStepResult] = []
        self._audit.log("routine_started", {"routine": routine.name, "step_count": len(routine.steps)})
        for step in routine.steps:
            validation_error = self.validate_step(step.tool_name, step.args)
            if validation_error is not None:
                result = RoutineStepResult(
                    routine_name=routine.name,
                    step_id=step.id,
                    tool_name=step.tool_name,
                    risk=RiskLevel.HIGH,
                    status="blocked",
                    message=validation_error,
                    blocked=True,
                )
                results.append(result)
                self._log_step(result)
                return RoutineExecutionResult(routine.name, "blocked", results, validation_error)

            spec_and_handler = self._tools.get(step.tool_name)
            assert spec_and_handler is not None
            spec, handler = spec_and_handler
            decision = self._permissions.evaluate(step.tool_name, spec.risk)

            if decision.decision is PermissionDecision.BLOCK:
                result = RoutineStepResult(
                    routine_name=routine.name,
                    step_id=step.id,
                    tool_name=step.tool_name,
                    risk=spec.risk,
                    status="blocked",
                    message=decision.reason,
                    blocked=True,
                )
                results.append(result)
                self._log_step(result)
                return RoutineExecutionResult(routine.name, "blocked", results, decision.reason)

            if decision.decision is PermissionDecision.REQUIRE_CONFIRMATION and not confirm_medium:
                result = RoutineStepResult(
                    routine_name=routine.name,
                    step_id=step.id,
                    tool_name=step.tool_name,
                    risk=spec.risk,
                    status="confirmation_required",
                    message=decision.reason,
                    requires_confirmation=True,
                )
                results.append(result)
                self._log_step(result)
                return RoutineExecutionResult(routine.name, "confirmation_required", results, decision.reason)

            exec_result = handler(step.args)
            result = RoutineStepResult(
                routine_name=routine.name,
                step_id=step.id,
                tool_name=step.tool_name,
                risk=spec.risk,
                status=exec_result.status,
                message=exec_result.message,
                data=exec_result.data,
            )
            results.append(result)
            self._log_step(result)

        message = f"Routine '{routine.name}' completed." if results else "Routine has no steps."
        self._audit.log("routine_completed", {"routine": routine.name, "status": "ok"})
        return RoutineExecutionResult(routine.name, "ok", results, message)

    def validate_step(self, tool_name: str, args: dict[str, object]) -> str | None:
        spec_and_handler = self._tools.get(tool_name)
        if spec_and_handler is None:
            return f"Unknown tool '{tool_name}' in routine step."

        if "command" in args or "shell" in args or "raw" in args:
            return "Raw shell arguments are forbidden in routine steps."

        spec, _ = spec_and_handler
        if spec.requires_trusted_app:
            trusted_app = str(args.get("app", "")).strip().lower()
            if not trusted_app:
                return "Trusted app target is required."
            if not self._trusted.is_app_trusted(trusted_app):
                return f"App '{trusted_app}' is not allowlisted."

        if spec.requires_trusted_path:
            raw_path = str(args.get("path", "")).strip()
            if not raw_path:
                return "Trusted path target is required."
            validation = self._validate_trusted_path(raw_path)
            if not validation.ok:
                return validation.reason

        return None

    def _validate_trusted_path(self, raw_path: str) -> TrustedValidationResult:
        path = Path(raw_path).expanduser().resolve()
        for trusted in self._trusted.list_trusted_paths():
            trusted_root = Path(trusted).expanduser().resolve()
            if str(path).startswith(str(trusted_root)):
                return TrustedValidationResult(ok=True)
        return TrustedValidationResult(ok=False, reason=f"Path '{raw_path}' is not inside a trusted folder.")

    def _log_step(self, step: RoutineStepResult) -> None:
        self._audit.log(
            "routine_step",
            {
                "routine": step.routine_name,
                "step_id": step.step_id,
                "tool": step.tool_name,
                "risk": step.risk.value,
                "status": step.status,
                "message": step.message,
            },
        )
