"""Runs on the manufacturer's own machine, started by their own SuperNode.

This is the only component that touches the technical file, and the path is
set by the node operator with --node-config. Nothing the coordinator sends can
change it.

The file is read here, evaluated here, and discarded when this function
returns. What crosses the network is a list of claims that already passed the
egress contract and the disclosure ledger — both of which also run here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flwr.app import ConfigRecord, Context, Error, Message, RecordDict
from flwr.clientapp import ClientApp

from local_node.ledger import Ledger, minimum_sufficient
from local_node.schema import EgressViolation, confidential_strings, validate_claim

_APP_ERROR = 2

app = ClientApp()


def _find(evidence: dict[str, Any], quantity: str, distance: float | None):
    """Pick the evidence entry that matches the clause, including test distance."""
    for entry in evidence.get(quantity, []):
        if distance is None or entry.get("distance_m") == distance:
            return entry
    return None


def _assess(clause: dict[str, Any], tf: dict[str, Any], ledger: Ledger,
            jurisdiction: str) -> dict[str, Any]:
    """Deterministic clause assessment. No model, no network."""
    quantity = clause.get("quantity")
    limit = clause.get("limit") or {}
    distance = limit.get("distance_m")
    entry = _find(tf["evidence"], quantity, distance) if quantity else None

    if entry is None:
        return {"clause_id": clause["clause_id"], "status": "UNSUPPORTED",
                "note": "No evidence matching this clause and its test conditions."}

    claim: dict[str, Any] = {
        "clause_id": clause["clause_id"],
        "evidence_ref": entry.get("report"),
        "evidence_commit": entry.get("commit"),
    }

    if limit:
        value = entry["value"]
        ok = value <= limit["value"] if limit.get("comparison", "<=") == "<=" else value >= limit["value"]
        claim["status"] = "PASS" if ok else "FAIL"
        claim["limit"] = {k: v for k, v in limit.items() if k in {"value", "unit", "distance_m"}}
        # Minimum sufficient: the clause asks which side of the limit, so answer
        # in one bit. The measured value is more than the regulation requires.
        if minimum_sufficient(clause) == "bit":
            ledger.record(f"{quantity}@{int(distance)}" if distance else quantity,
                          "bit", clause["clause_id"], jurisdiction)
            claim["measured"] = None
            claim["note"] = "Verdict given against the published limit."
        else:
            claim["measured"] = {"value": value, "unit": entry.get("unit", "")}
            claim["note"] = "Measured value released."
    else:
        expected = str(clause.get("expected", "")).lower()
        actual = str(entry["value"]).lower()
        claim["status"] = "PASS" if expected and expected in actual else "UNSUPPORTED"
        claim["note"] = ("Evidence matches the named standard." if claim["status"] == "PASS"
                         else "Evidence does not establish the named standard.")
    return claim


@app.query("assess")
def assess(msg: Message, context: Context) -> Message:
    """Assess the local technical file and return claims only."""
    raw_dir = context.node_config.get("data-dir")
    if not raw_dir:
        return Message(
            Error(_APP_ERROR, "This SuperNode has no 'data-dir' in its --node-config, "
                              "so there is no technical file to assess."),
            reply_to=msg)

    path = Path(str(raw_dir)).expanduser() / "technical_file.json"
    if not path.is_file():
        return Message(Error(_APP_ERROR, f"No technical_file.json in {raw_dir}"), reply_to=msg)

    technical_file = json.loads(path.read_text())
    forbidden = confidential_strings(technical_file)

    payload = json.loads(str(msg.content["request"]["json"]))
    ledger = Ledger.from_json(payload.get("ledger") or "")
    jurisdiction = payload.get("jurisdiction", "?")

    claims = []
    for clause in payload["clauses"]:
        draft = _assess(clause, technical_file, ledger, jurisdiction)
        try:
            claims.append(validate_claim(draft, forbidden=forbidden))
        except (EgressViolation, TypeError) as exc:
            claims.append({"clause_id": draft.get("clause_id", "?"), "status": "REFUSED",
                           "note": f"Blocked by egress contract: {exc}"[:200]})

    # ---- THE RED LINE -------------------------------------------------
    # `technical_file` goes out of scope when this returns. The reply below is
    # everything that leaves this machine: clause ids, verdicts, report
    # references, and the ledger. No document text, no file, no paths.
    out = {
        "manufacturer": technical_file["manufacturer"],
        "claims": claims,
        "ledger": ledger.summary(),
        "ledger_state": ledger.to_json(),
        "documents_transmitted": 0,
    }
    return Message(
        RecordDict({"reply": ConfigRecord({"json": json.dumps(out)})}), reply_to=msg)
