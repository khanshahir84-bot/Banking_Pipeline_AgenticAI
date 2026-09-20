"""Shared types for deterministic banking-agent guardrails."""
from dataclasses import dataclass, field
from enum import Enum


class GuardrailStage(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True)
class GuardrailFinding:
    """A non-sensitive guardrail decision recorded in traces and audit events."""
    name: str
    action: str
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class InputAssessment:
    sanitized_message: str
    intent: str | None
    findings: tuple[GuardrailFinding, ...] = ()


@dataclass(frozen=True)
class OutputAssessment:
    response: str
    findings: tuple[GuardrailFinding, ...] = ()


class GuardrailRejected(Exception):
    """Raised when a safety policy intentionally stops a workflow."""

    def __init__(self, stage: GuardrailStage, reason: str, public_message: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.public_message = public_message
        self.finding = GuardrailFinding(name=reason, action="blocked")
