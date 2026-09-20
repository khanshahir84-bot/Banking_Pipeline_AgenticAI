"""Backward-compatible PII redaction facade for all application boundaries."""
from .guardrails.pii import PIIRedactionResult, PIIRedactor, redactor


def redact(text: str) -> str:
    """Return text with detected sensitive values fully replaced."""
    return redactor.redact(text).text


__all__ = ["PIIRedactionResult", "PIIRedactor", "redact", "redactor"]
