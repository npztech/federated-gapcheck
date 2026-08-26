"""Jurisdiction agent.

Holds one national rulebook. Two modes, selected by whether claims are supplied:

  decompose   no claims given -> emit one clause query per rule
  adjudicate  claims given    -> rule on each clause, and say what is still missing

Rulebooks are public, so this agent keeps no secrets. It never sees a technical
file; it only ever sees claims that passed the manufacturer's egress contract.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from flwr.agentapp import AgentApp, AgentSession
from flwr.app import Context
from openai import OpenAI

MODEL = "openai/gpt-5.6-sol"
FIXTURES = Path(__file__).parent / "fixtures"

app = AgentApp()

INSTRUCTIONS = """You are a conformity assessment agent for one jurisdiction. You \
are given the clauses of your rulebook and the claims a manufacturer returned.

You never see the manufacturer's technical file. Judge only what the claims state.

Reply with a single JSON object and nothing else:
{"jurisdiction": str,
 "clauses": [{"clause_id": str, "verdict": "PASS"|"FAIL"|"INSUFFICIENT",
              "reason": str, "evidence_ref": str or null,
              "followup": str or null}],
 "market_access": "GRANTED"|"REFUSED"|"BLOCKED_PENDING_EVIDENCE",
 "summary": str}

Rules:
- A claim only satisfies a clause if it matches the required quantity AND the
  required test conditions. A measurement at the wrong distance is INSUFFICIENT,
  never PASS.
- A threshold clause asks whether a quantity sits on one side of a published
  limit. A claim of PASS against that limit, carrying an evidence reference, is
  SUFFICIENT on its own. "measured": null is normal and expected - the
  manufacturer is not obliged to disclose the measured value, and you must not
  mark a clause INSUFFICIENT merely because the number was withheld. Judge the
  assertion, not the disclosure.
- A claimed standard must match the one the clause names. A different standard
  is INSUFFICIENT unless the clause allows equivalents.
- Set followup to one specific question when INSUFFICIENT, otherwise null.
- market_access is GRANTED only when every clause is PASS.
- Cite the manufacturer's evidence_ref when you rely on it.
"""


def load_rulebook(name: str) -> dict[str, Any]:
    path = FIXTURES / f"rules_{name.lower()}.json"
    if not path.exists():
        raise ValueError(f"unknown rulebook {name!r}")
    return json.loads(path.read_text())


def clause_queries(rulebook: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn the rulebook into queries a manufacturer agent can answer.

    The quantity and limit travel with the query so the manufacturer's
    disclosure ledger can price the answer before releasing it.
    """
    out = []
    for c in rulebook["clauses"]:
        out.append(
            {
                "clause_id": c["id"],
                "title": c["title"],
                "query": f"{c['id']} | {c['title']} | {c['requirement']}",
                "quantity": c.get("quantity"),
                "limit": c.get("limit"),
                "expected": c.get("expected"),
            }
        )
    return out


def parse_obj(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("model did not return a JSON object")
    return json.loads(text[start : end + 1])


@app.main()
def main(agent: AgentSession, context: Context) -> None:
    rc = context.run_config
    rulebook = load_rulebook(str(rc.get("agent.rulebook", "uk")))
    raw_claims = str(rc.get("agent.claims-b64") or "").strip()

    agent.events.emit(
        {
            "type": "compliance.rulebook.loaded",
            "jurisdiction": rulebook["jurisdiction"],
            "clauses": len(rulebook["clauses"]),
            "sources": rulebook["sources"],
        }
    )

    # ---- decompose -------------------------------------------------------
    if not raw_claims:
        queries = clause_queries(rulebook)
        for q in queries:
            agent.events.emit({"type": "compliance.clause.query", **q})
        print(json.dumps({"jurisdiction": rulebook["jurisdiction"], "queries": queries}, indent=2))
        return

    # ---- adjudicate ------------------------------------------------------
    claims = json.loads(base64.b64decode(raw_claims).decode())
    agent.events.emit(
        {"type": "compliance.claims.received", "count": len(claims),
         "jurisdiction": rulebook["jurisdiction"]}
    )

    client = OpenAI(
        base_url=os.environ["FLWR_RUNTIME_BASE_URL"],
        api_key=os.environ["FLWR_RUNTIME_API_KEY"],
        max_retries=0,
    )
    response = client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=json.dumps({"rulebook": rulebook, "claims": claims}),
        stream=False,
    )
    report = parse_obj(response.output_text)
    report.setdefault("jurisdiction", rulebook["jurisdiction"])

    for clause in report.get("clauses", []):
        agent.events.emit({"type": "compliance.verdict", **clause})
    agent.events.emit(
        {
            "type": "compliance.market_access",
            "jurisdiction": report["jurisdiction"],
            "decision": report.get("market_access"),
        }
    )

    print(json.dumps(report, indent=2))
