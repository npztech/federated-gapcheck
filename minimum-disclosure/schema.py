"""The egress contract.

Everything a manufacturer agent is allowed to say about its device must fit in
a Claim. Claims have fixed fields and a bounded note, so the channel between
organisations has a provable upper bound on what it can carry.

This module is vendored into each AgentApp rather than shared as a package,
because a Flower App Bundle ships its own dependencies.
"""

from __future__ import annotations

import json
from typing import Any

# --------------------------------------------------------------------------
# Claim
# --------------------------------------------------------------------------
STATUSES = ("PASS", "FAIL", "UNSUPPORTED", "REFUSED")

CLAIM_FIELDS = {
    "clause_id": str,
    "status": str,
    "measured": (dict, type(None)),
    "limit": (dict, type(None)),
    "evidence_ref": (str, type(None)),
    "note": str,
}

MEASURE_FIELDS = {"value", "unit", "distance_m"}
NOTE_MAX_CHARS = 200


class EgressViolation(Exception):
    """Raised when a payload would carry more than the contract permits."""


def validate_claim(claim: Any, *, forbidden: list[str] | None = None) -> dict[str, Any]:
    """Check one claim against the contract. Raise if it does not conform.

    `forbidden` holds strings drawn from the confidential section of the local
    technical file. They must never appear in an outgoing claim.
    """
    if not isinstance(claim, dict):
        raise EgressViolation("claim must be an object")

    unknown = set(claim) - set(CLAIM_FIELDS)
    if unknown:
        raise EgressViolation(f"claim carries fields outside the contract: {sorted(unknown)}")

    missing = {"clause_id", "status", "note"} - set(claim)
    if missing:
        raise EgressViolation(f"claim is missing required fields: {sorted(missing)}")

    for field, expected in CLAIM_FIELDS.items():
        if field in claim and not isinstance(claim[field], expected):
            raise EgressViolation(f"field {field!r} has the wrong type")

    if claim["status"] not in STATUSES:
        raise EgressViolation(f"status must be one of {STATUSES}")

    if len(claim["note"]) > NOTE_MAX_CHARS:
        raise EgressViolation(
            f"note is {len(claim['note'])} chars, limit is {NOTE_MAX_CHARS}"
        )

    for field in ("measured", "limit"):
        value = claim.get(field)
        if isinstance(value, dict):
            extra = set(value) - MEASURE_FIELDS
            if extra:
                raise EgressViolation(f"{field} carries unexpected keys: {sorted(extra)}")

    haystack = json.dumps(claim).lower()
    for secret in forbidden or []:
        if secret and secret.lower() in haystack:
            raise EgressViolation(f"claim would disclose confidential value {secret!r}")

    return claim


def confidential_strings(technical_file: dict[str, Any]) -> list[str]:
    """Flatten the confidential section into strings that must not leak."""
    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key != "comment":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str) and len(node) > 3:
            out.append(node)

    walk(technical_file.get("_confidential", {}))
    return out


# --------------------------------------------------------------------------
# Egress log — what actually crossed the boundary
# --------------------------------------------------------------------------
class EgressLog:
    """Counts every byte that leaves this organisation."""

    def __init__(self) -> None:
        self.claims: list[dict[str, Any]] = []
        self.rejected: list[str] = []

    def record(self, claim: dict[str, Any]) -> None:
        self.claims.append(claim)

    def reject(self, reason: str) -> None:
        self.rejected.append(reason)

    def summary(self) -> dict[str, Any]:
        payload = json.dumps(self.claims)
        return {
            "claims_emitted": len(self.claims),
            "claims_rejected": len(self.rejected),
            "bytes_crossed": len(payload.encode()),
            "raw_evidence_bytes_crossed": 0,
        }
