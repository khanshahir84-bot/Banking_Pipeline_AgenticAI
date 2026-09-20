"""Input guardrails: PII, injection, banking scope, and safety policy."""
from __future__ import annotations

import re

from fastapi import HTTPException

from ..agents.routing import classify, policy_for
from ..security import require_scope
from .models import GuardrailFinding, GuardrailRejected, GuardrailStage, InputAssessment
from .pii import PIIRedactor, redactor

# Match explicit attempts to change the trusted system/tool boundary, rather than
# ordinary customer language such as "ignore a pending transaction".
_INJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction_override", re.compile(r"\b(?:ignore|disregard|override|bypass)\b.{0,80}\b(?:previous|prior|system|instructions?|rules?|guardrails?)\b", re.I | re.S)),
    ("role_impersonation", re.compile(r"\b(?:act as|you are now|switch to)\b.{0,50}\b(?:system|developer|admin|root)\b", re.I | re.S)),
    ("prompt_exfiltration", re.compile(r"\b(?:reveal|show|print|repeat|extract)\b.{0,80}\b(?:system prompt|hidden prompt|developer message|instructions?)\b", re.I | re.S)),
    ("tool_exfiltration", re.compile(r"\b(?:api[ _-]?key|access token|secret|password)\b.{0,80}\b(?:reveal|show|print|send|exfiltrate)\b", re.I | re.S)),
)

# The service is not an emergency, criminal-facilitation, or abusive-content
# channel. These narrow rules avoid treating normal banking terms as unsafe.
_UNSAFE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("self_harm", re.compile(r"\b(?:kill myself|suicide|self[- ]harm)\b", re.I)),
    ("violent_threat", re.compile(r"\b(?:kill|shoot|bomb|attack)\b.{0,50}\b(?:person|people|bank|branch|employee|them)\b", re.I | re.S)),
    ("financial_crime", re.compile(r"\b(?:launder money|money laundering|forge(?:ry)?|counterfeit|steal (?:an )?(?:card|identity)|evade sanctions)\b", re.I)),
    ("sexual_content", re.compile(r"\b(?:child sexual|sexual abuse|explicit sexual)\b", re.I)),
)


class InputGuardrails:
    def __init__(self, pii_redactor: PIIRedactor = redactor):
        self._pii_redactor = pii_redactor

    def assess(self, message: str, user: dict) -> InputAssessment:
        """Redact first, then block unsafe/untrusted instructions before routing."""
        redaction = self._pii_redactor.redact(message)
        findings: list[GuardrailFinding] = []
        if redaction.categories:
            findings.append(GuardrailFinding("pii_redaction", "redacted", redaction.categories))

        self._reject_if_matches(redaction.text, _INJECTION_RULES, "prompt_injection")
        self._reject_if_matches(redaction.text, _UNSAFE_RULES, "content_safety")

        intent = classify(redaction.text)
        if intent is None:
            raise GuardrailRejected(GuardrailStage.INPUT, "scope_validation", "I can only help with supported banking requests: balances, transactions, statements, address changes, cheque books, and KYC updates.")

        # This is intentionally before specialist/tool execution. Translate an
        # authorization failure into a traceable input guardrail decision.
        try:
            required_scope = policy_for(intent).required_scope
            require_scope(user, required_scope)
        except HTTPException as exc:
            raise GuardrailRejected(GuardrailStage.INPUT, "scope_validation", "You are not authorized to perform that banking request.") from exc
        findings.append(GuardrailFinding("scope_validation", "passed", (intent,)))
        return InputAssessment(redaction.text, intent, tuple(findings))

    @staticmethod
    def _reject_if_matches(text: str, rules: tuple[tuple[str, re.Pattern[str]], ...], reason: str) -> None:
        categories = tuple(name for name, pattern in rules if pattern.search(text))
        if categories:
            public = "I can’t help with that request. I can assist with supported banking requests." if reason == "content_safety" else "I can’t follow instructions that attempt to change my security controls. Please make a supported banking request."
            error = GuardrailRejected(GuardrailStage.INPUT, reason, public)
            error.finding = GuardrailFinding(reason, "blocked", categories)
            raise error
