"""Allow-listed banking intent routing and authorization metadata."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentPolicy:
    name: str
    required_scope: str


INTENT_POLICIES = {
    "balance": IntentPolicy("balance", "accounts:read"),
    "transaction": IntentPolicy("transaction", "transactions:read"),
    "statement": IntentPolicy("statement", "transactions:read"),
    "address_change": IntentPolicy("address_change", "service:write"),
    "cheque_book": IntentPolicy("cheque_book", "service:write"),
    "kyc": IntentPolicy("kyc", "service:write"),
}
_INTENT_RULES = (("balance", "balance"), ("statement", "statement"), ("transaction", "transaction"), ("address_change", "address"), ("cheque_book", "cheque"), ("kyc", "kyc"))


def classify(text: str) -> str | None:
    """Classify only explicitly supported customer intents, deterministically."""
    lowered = text.lower()
    return next((intent for word, intent in _INTENT_RULES if word in lowered), None)


def policy_for(intent: str) -> IntentPolicy:
    return INTENT_POLICIES[intent]
