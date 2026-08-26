"""Manufacturer agent.

Runs inside the manufacturer's own federation. Holds the device technical file
and answers clause queries from any number of regulators, over time.

Three layers, in this order:

  1. the confidential section of the technical file never enters the model
     context, so the model cannot disclose what it never saw
  2. the model DRAFTS a claim; it does not decide what may leave
  3. the disclosure ledger prices the draft against everything already
     released - including releases made to a different regulator, in a
     different jurisdiction, on a different day - and downgrades or refuses

Layer 3 is the point. A single answer is rarely disclosive; a sequence is.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
from pathlib import Path
from typing import Any

from flwr.agentapp import AgentApp, AgentSession
from flwr.app import ConfigRecord, Context
from openai import OpenAI

from mfr_agent.ledger import Ledger, minimum_sufficient
from mfr_agent.schema import (
    EgressLog,
    scrub_note,
    EgressViolation,
    confidential_strings,
    validate_claim,
)

MODEL = "openai/gpt-5.6-sol"
FIXTURES = Path(__file__).parent / "fixtures"
LEDGER_KEY = "disclosure_ledger"

app = AgentApp()

INSTRUCTIONS = """You are a manufacturer's compliance agent. A regulator has asked \
about one or more clauses. Answer using only the evidence provided.

Reply with a single JSON object {"claims": [...]}, one claim per clause, in order:
{"clause_id": str, "status": "PASS"|"FAIL"|"UNSUPPORTED"|"REFUSED",
 "measured": {"value": number, "unit": str, "distance_m": number} or null,
 "limit": {"value": number, "unit": str, "distance_m": number} or null,
 "evidence_ref": str or null,
 "evidence_commit": str or null, "note": str}

Rules:
- Match the clause's test conditions, including distance. If the clause names a
  distance and no measurement at that distance exists, status is UNSUPPORTED.
- If no relevant evidence exists, status is UNSUPPORTED.
- If asked for anything other than clause conformity, status is REFUSED.
- evidence_commit is the "commit" field of the evidence entry you relied on. Copy
  it exactly. It lets an inspector verify the report was not altered afterwards.
- note is under 200 characters and never names suppliers, costs, part numbers,
  repositories or schematics.
"""


def load_technical_file(name: str, supplied_b64: str = "") -> dict[str, Any]:
    """Load the technical file.

    A manufacturer supplies their own file at run time. The bundled fixtures
    are a demo convenience only: shipping every manufacturer's file inside one
    App Bundle would put a competitor's data in your bundle, which is exactly
    what this system exists to prevent.
    """
    if supplied_b64:
        return json.loads(base64.b64decode(supplied_b64).decode())
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        raise ValueError(f"unknown technical file {name!r}")
    return json.loads(path.read_text())


def disclosable_view(technical_file: dict[str, Any]) -> dict[str, Any]:
    """What the model may see. The confidential block is dropped here."""
    return {"device": technical_file["device"], "evidence": technical_file["evidence"]}


def quantity_key(clause: dict[str, Any]) -> str | None:
    """Ledger key for the quantity a clause asks about, including test distance."""
    quantity = clause.get("quantity")
    if not quantity:
        return None
    limit = clause.get("limit") or {}
    distance = limit.get("distance_m")
    return f"{quantity}@{int(distance)}" if distance else quantity


def parse_claims(text: str) -> list[dict[str, Any]]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise EgressViolation("model did not return a JSON object")
    obj = json.loads(text[start : end + 1])
    claims = obj.get("claims", obj)
    return claims if isinstance(claims, list) else [claims]


ANSWER = {
    "PASS": "YES",
    "FAIL": "NO",
    "UNSUPPORTED": "NOT_ESTABLISHED",
    "REFUSED": "WITHHELD",
}


def to_csv(claims: list[dict[str, Any]], clauses: list[dict[str, Any]],
           decisions: list[dict[str, Any]]) -> str:
    """The compliance matrix that actually leaves the building.

    One row per clause, a yes/no answer, the report it rests on, and what that
    answer cost in disclosure. This file is the entire outward transfer.
    """
    titles = {c.get("clause_id"): c.get("title", "") for c in clauses}
    bits = {d.get("clause_id"): d.get("cost_bits", 0.0) for d in decisions}
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        ["clause_id", "requirement", "compliant", "evidence_ref", "disclosure_bits", "note"]
    )
    for claim in claims:
        cid = claim.get("clause_id", "")
        writer.writerow(
            [
                cid,
                titles.get(cid, ""),
                ANSWER.get(claim.get("status", ""), "WITHHELD"),
                claim.get("evidence_ref") or "",
                round(float(bits.get(cid, 0.0)), 2),
                (claim.get("note") or "")[:120],
            ]
        )
    return buf.getvalue()


def refusal(clause_id: str, reason: str) -> dict[str, Any]:
    return {
        "clause_id": clause_id,
        "status": "REFUSED",
        "note": f"Blocked by egress contract: {reason}"[:200],
    }


def load_ledger(context: Context, rc_blob: str) -> Ledger:
    """Prefer state threaded by the coordinator, fall back to run-series state."""
    if rc_blob:
        return Ledger.from_json(base64.b64decode(rc_blob).decode())
    record = context.state.config_records.get(LEDGER_KEY)
    if record is not None:
        return Ledger.from_json(str(record.get("json", "")))
    return Ledger()


def save_ledger(context: Context, ledger: Ledger) -> None:
    """Persist into the run series, so a reused series keeps its memory."""
    context.state.config_records[LEDGER_KEY] = ConfigRecord({"json": ledger.to_json()})


@app.main()
def main(agent: AgentSession, context: Context) -> None:
    rc = context.run_config
    technical_file = load_technical_file(
        str(rc.get("agent.technical-file", "")),
        str(rc.get("agent.technical-file-b64") or "").strip(),
    )
    forbidden = confidential_strings(technical_file)
    log = EgressLog()
    jurisdiction = str(rc.get("agent.jurisdiction", "?"))

    raw = str(rc.get("agent.queries-b64") or "").strip()
    if raw:
        clauses = json.loads(base64.b64decode(raw).decode())
    else:
        single = str(rc.get("agent.query") or rc.get("agent.input") or "").strip()
        if not single:
            raise ValueError("set agent.queries-b64, agent.query or agent.input")
        clauses = [{"clause_id": "adhoc", "query": single}]

    ledger = load_ledger(context, str(rc.get("agent.ledger-b64") or "").strip())

    agent.events.emit(
        {
            "type": "compliance.query.received",
            "manufacturer": technical_file["manufacturer"],
            "device": technical_file["device"],
            "jurisdiction": jurisdiction,
            "clauses": len(clauses),
            "bits_already_disclosed": round(ledger.total_spent(), 2),
        }
    )

    client = OpenAI(
        base_url=os.environ["FLWR_RUNTIME_BASE_URL"],
        api_key=os.environ["FLWR_RUNTIME_API_KEY"],
        max_retries=0,
    )
    response = client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=json.dumps(
            {
                "clauses": [c.get("query", c) for c in clauses],
                "available_evidence": disclosable_view(technical_file),
            }
        ),
        stream=False,
    )

    try:
        drafts = parse_claims(response.output_text)
    except (EgressViolation, json.JSONDecodeError) as exc:
        log.reject(str(exc))
        drafts = [refusal("unknown", str(exc))]

    claims, decisions = [], []
    for clause, draft in zip(clauses, drafts + [{}] * len(clauses)):
        withheld_value = False
        if not isinstance(draft, dict):
            draft = refusal(clause.get("clause_id", "unknown"), "malformed draft")

        # ---- layer 3: minimum sufficient disclosure, then the ledger -----
        key = quantity_key(clause)

        # A free-text question carries no quantity or limit, so the ledger has
        # nothing to price. That is exactly when a value must not leave: an
        # unstructured ask is the easiest way to walk a number out of the
        # building. Unpriced means unreleased.
        if not key and isinstance(draft.get("measured"), dict):
            withheld_value = True
            draft["measured"] = None
            draft["note"] = scrub_note(
                str(draft.get("note", ""))
                + " Value withheld: this question cites no clause limit, so the"
                " disclosure cannot be priced."
            ).strip()[:200]
            agent.events.emit(
                {"type": "compliance.disclosure.withheld",
                 "clause_id": clause.get("clause_id"), "reason": "unpriced"}
            )

        if key and isinstance(draft.get("measured"), dict):
            # Default to the least that resolves the clause. Releasing the
            # measured value is an escalation the regulator must ask for.
            wanted = minimum_sufficient(clause)
            if wanted == "bit" and not bool(rc.get("agent.request-exact")):
                ledger.record(key, "bit", str(clause.get("clause_id")), jurisdiction)
                draft["measured"] = None
                withheld_value = True
                draft["note"] = scrub_note(
                    str(draft.get("note", ""))
                ).strip()[:160] + " Value not required by this clause."
                decisions.append(
                    {"clause_id": clause.get("clause_id"), "quantity": key,
                     "allowed": True, "released": "bit", "cost_bits": 1.0,
                     "reason": "minimum sufficient"}
                )
                agent.events.emit(
                    {"type": "compliance.disclosure.minimised",
                     "clause_id": clause.get("clause_id"), "quantity": key,
                     "released": "bit"}
                )
                try:
                    claim = validate_claim(draft, forbidden=forbidden)
                    log.record(claim)
                except (EgressViolation, TypeError) as exc:
                    log.reject(str(exc))
                    claim = refusal(str(draft.get("clause_id", "unknown")), str(exc))
                claims.append(claim)
                agent.events.emit({"type": "compliance.claim.emitted", "claim": claim})
                continue

            decision = ledger.adjudicate(key, "exact")
            # Record what was ACTUALLY released, not what was asked for.
            actual = dict(decision)
            actual["released"] = "exact" if decision["allowed"] else "bit"
            if not decision["allowed"]:
                actual["cost_bits"] = 1.0
                actual["requested_cost_bits"] = decision["cost_bits"]
            decisions.append({"clause_id": clause.get("clause_id"), "quantity": key, **actual})

            if decision["allowed"]:
                ledger.record(key, "exact", str(clause.get("clause_id")), jurisdiction)
            else:
                # Withhold the value, keep the verdict. The clause still resolves.
                exposes = decision.get("exposes") or []
                if decision["reason"] == "differencing":
                    via = ", ".join(
                        f"{c['clause_id']}/{c['jurisdiction']}"
                        for e in exposes for c in e["because_of"]
                    )
                    why = (
                        f"Value withheld: with {via} it would pin "
                        f"{exposes[0]['derived']} to +-{exposes[0]['residual_dB']} dB."
                    )
                else:
                    why = (
                        f"Value withheld: disclosure budget spent "
                        f"({decision['spent_total']}/{decision['budget_bits']} bits)."
                    )
                withheld_value = True
                draft["measured"] = None
                draft["note"] = scrub_note(
                    str(draft.get("note", "")) + " " + why
                ).strip()[:200]
                ledger.record(key, "bit", str(clause.get("clause_id")), jurisdiction)
                agent.events.emit(
                    {
                        "type": "compliance.disclosure.withheld",
                        "clause_id": clause.get("clause_id"),
                        "quantity": key,
                        "reason": decision["reason"],
                        "exposes": exposes,
                    }
                )

        # ---- layer 2: the egress contract -------------------------------
        try:
            claim = validate_claim(
                draft,
                forbidden=forbidden,
                # Only when a measured value was actually withheld. Public
                # standard numbers like "UL 62368-1" are not secrets.
                note_must_be_numeric_free=withheld_value,
            )
            log.record(claim)
        except (EgressViolation, TypeError) as exc:
            log.reject(str(exc))
            claim = refusal(str(draft.get("clause_id", "unknown")), str(exc))
            agent.events.emit({"type": "compliance.egress.blocked", "reason": str(exc)[:200]})

        claims.append(claim)
        agent.events.emit({"type": "compliance.claim.emitted", "claim": claim})

    matrix = to_csv(claims, clauses, decisions)
    agent.events.emit({"type": "compliance.matrix.csv", "csv": matrix})

    save_ledger(context, ledger)
    agent.events.emit({"type": "compliance.ledger.summary", **ledger.summary()})
    agent.events.emit({"type": "compliance.egress.summary", **log.summary()})

    print(
        json.dumps(
            {
                "claims": claims,
                "csv": matrix,
                "egress": log.summary(),
                "ledger": ledger.summary(),
                "ledger_state_b64": base64.b64encode(ledger.to_json().encode()).decode(),
                "decisions": decisions,
            },
            indent=2,
        )
    )
