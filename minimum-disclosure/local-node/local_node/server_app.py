"""Regulator side. Dispatches clauses to manufacturer SuperNodes.

The coordinator never sees a technical file. It sends a rulebook — which is
public — and receives claims. It does not hold a roster of what any node
contains, and it cannot read the node's disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from flwr.app import ConfigRecord, Context, Message, RecordDict
from flwr.serverapp import Grid, ServerApp

FIXTURES = Path(__file__).parent / "fixtures"
MESSAGE_TYPE = "query.assess"

app = ServerApp()


def load_rulebook(name: str) -> dict:
    return json.loads((FIXTURES / f"rules_{name.lower()}.json").read_text())


def clause_queries(rulebook: dict) -> list[dict]:
    return [{"clause_id": c["id"], "title": c["title"], "requirement": c["requirement"],
             "quantity": c.get("quantity"), "limit": c.get("limit"),
             "expected": c.get("expected")} for c in rulebook["clauses"]]


@app.main()
def main(grid: Grid, context: Context) -> None:
    rulebook = load_rulebook(str(context.run_config["rulebook"]))
    clauses = clause_queries(rulebook)

    node_ids = list(grid.get_node_ids())
    if not node_ids:
        raise RuntimeError(
            "No SuperNodes are connected, so there is nothing to assess. Start a "
            "`flower-supernode` with --node-config 'data-dir=\"...\"' and run again.")

    print(f"\nDispatching {len(clauses)} clauses of {rulebook['jurisdiction']} "
          f"to {len(node_ids)} manufacturer node(s)...\n")

    request = json.dumps({"clauses": clauses,
                          "jurisdiction": rulebook["jurisdiction"],
                          "ledger": ""})
    content = RecordDict({"request": ConfigRecord({"json": request})})
    replies = grid.send_and_receive(
        [Message(content, dst_node_id=n, message_type=MESSAGE_TYPE, group_id="1")
         for n in node_ids],
        timeout=120)

    transmitted = 0
    for reply in replies:
        if reply.has_error():
            print(f"  node {reply.metadata.src_node_id}: {reply.error.reason}")
            continue
        out = json.loads(str(reply.content["reply"]["json"]))
        transmitted += out["documents_transmitted"]
        print(f"  {out['manufacturer']}")
        for c in out["claims"]:
            print(f"    {c['clause_id']:<10} {c['status']:<12} "
                  f"measured={c.get('measured')}  {c.get('evidence_ref') or '-'}")
        print(f"    ledger: {out['ledger']['bits_disclosed_total']} bits\n")

    print(f"  documents transmitted: {transmitted}")
