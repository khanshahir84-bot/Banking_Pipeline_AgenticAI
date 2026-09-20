"""Output guardrails: groundedness, safety, and response contract validation."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from .models import GuardrailFinding, GuardrailRejected, GuardrailStage, OutputAssessment
from .pii import PIIRedactor, redactor

# These facts must never be introduced by synthesis unless represented by the
# approved tool payload. Numeric/account-like facts are covered separately.
_UNSUPPORTED_CLAIMS = re.compile(r"\b(?:approved|declined|closed|frozen|transferred|refunded|charged|waived|guaranteed)\b", re.I)
_UNSAFE_OUTPUT = re.compile(r"\b(?:kill yourself|suicide|hate (?:you|them)|make a bomb|launder money|password|api[ _-]?key)\b", re.I)
_SECRET_REQUEST = re.compile(r"\b(?:send|provide|share|enter)\b.{0,45}\b(?:password|pin|one[- ]time code|security code|cvv)\b", re.I | re.S)
_MONEY_OR_LONG_NUMBER = re.compile(r"(?:[$£€]\s?\d[\d,.]*|\b\d{5,}\b|\b(?:balance|amount|total|available)\b.{0,14}?\b\d[\d,]*(?:\.\d{1,2})?\b)", re.I)
_URL = re.compile(r"https?://\S+", re.I)


class OutputGuardrails:
    """Reject unsafe or ungrounded model text and use a deterministic fallback."""

    def __init__(self, pii_redactor: PIIRedactor = redactor):
        self._pii_redactor = pii_redactor

    def assess(self, response: str, approved_data: dict[str, Any]) -> OutputAssessment:
        if not isinstance(response, str) or not response.strip() or len(response) > 4000:
            raise GuardrailRejected(GuardrailStage.OUTPUT, "response_validation", "Your request was completed. Please check your secure banking channel for the result.")
        if any(ord(char) < 32 and char not in "\n\t" for char in response) or _URL.search(response) or _SECRET_REQUEST.search(response):
            raise GuardrailRejected(GuardrailStage.OUTPUT, "response_validation", "Your request was completed. Please check your secure banking channel for the result.")

        redaction = self._pii_redactor.redact(response)
        if redaction.categories:
            raise GuardrailRejected(GuardrailStage.OUTPUT, "response_validation", "Your request was completed. Please check your secure banking channel for the result.")
        if _UNSAFE_OUTPUT.search(response):
            raise GuardrailRejected(GuardrailStage.OUTPUT, "content_safety", "Your request was completed. Please check your secure banking channel for the result.")
        self._check_grounded(response, approved_data)
        return OutputAssessment(response.strip(), (GuardrailFinding("groundedness", "passed"), GuardrailFinding("content_safety", "passed"), GuardrailFinding("response_validation", "passed")))

    def fallback(self, approved_data: dict[str, Any]) -> str:
        """Return a bounded rendering sourced only from approved MCP data."""
        status = approved_data.get("status")
        delivery = approved_data.get("delivery")
        if status:
            return f"Your request status is {status.replace('_', ' ')}" + (f"; delivery is {delivery}." if delivery else ".")
        balance = approved_data.get("available_balance", approved_data.get("balance"))
        if balance is not None:
            currency = approved_data.get("currency", "")
            suffix = f" {currency}" if currency else ""
            return f"Your available balance is {balance}{suffix}."
        transactions = approved_data.get("transactions")
        if isinstance(transactions, list):
            return f"I found {len(transactions)} recent transactions in your banking record."
        return "Your request was completed. Please check your secure banking channel for the result."

    @staticmethod
    def _check_grounded(response: str, approved_data: dict[str, Any]) -> None:
        approved_values = {str(value) for value in _flatten(approved_data) if isinstance(value, (str, int, float))}
        for candidate in _MONEY_OR_LONG_NUMBER.findall(response):
            # A balance/amount phrase includes prose; compare its numeric part.
            numeric = re.search(r"[$£€]?\s?\d[\d,.]*", candidate)
            normalized = (numeric.group(0) if numeric else candidate).replace(" ", "")
            if not any(normalized in value.replace(" ", "") for value in approved_values):
                raise GuardrailRejected(GuardrailStage.OUTPUT, "groundedness", "Your request was completed. Please check your secure banking channel for the result.")
        # A model may describe a factual state only when that exact state was
        # returned by the relevant approved tool.
        claims = {claim.lower() for claim in _UNSUPPORTED_CLAIMS.findall(response)}
        approved_text = json.dumps(approved_data).lower()
        if any(claim not in approved_text for claim in claims):
            raise GuardrailRejected(GuardrailStage.OUTPUT, "groundedness", "Your request was completed. Please check your secure banking channel for the result.")


def _flatten(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item)
    else:
        yield value
