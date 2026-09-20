"""PII detection and redaction at every untrusted data boundary.

Patterns are deliberately conservative. They replace values rather than retaining
partial values, so storage, logs, prompts, and responses do not leak PII.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PIIRedactionResult:
    text: str
    categories: tuple[str, ...]


class PIIRedactor:
    _patterns: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("ssn", re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"), "[REDACTED-SSN]"),
        ("card", re.compile(r"\b(?:\d[ -]*?){12,19}\b"), "[REDACTED-CARD-OR-ACCOUNT]"),
        ("email", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
        ("phone", re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]?){1,2}\d{4}(?!\w)"), "[REDACTED-PHONE]"),
        ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE), "[REDACTED-IBAN]"),
    )

    def redact(self, text: str) -> PIIRedactionResult:
        categories: list[str] = []
        value = text
        for category, pattern, replacement in self._patterns:
            value, count = pattern.subn(replacement, value)
            if count:
                categories.append(category)
        return PIIRedactionResult(value, tuple(categories))


redactor = PIIRedactor()
