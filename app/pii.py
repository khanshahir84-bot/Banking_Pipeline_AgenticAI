"""Redacts sensitive values before LLM/evaluation/observability boundaries."""
import re
PATTERNS = [
 (re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"), "[REDACTED-SSN]"),
 (re.compile(r"\b\d{12,19}\b"), "[REDACTED-ACCOUNT]"),
 (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
]
def redact(text: str) -> str:
    for expression, replacement in PATTERNS: text = expression.sub(replacement, text)
    return text
