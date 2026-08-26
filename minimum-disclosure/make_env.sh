#!/usr/bin/env bash
# Produces the base64 clause payloads the demo commands need:
#   source make_env.sh          -> $UKQ, $USQ
#   $LED comes from a previous run's ledger_state_b64 (see below)
python3 - <<'PY' > /tmp/flwr_demo_env.sh
import base64, json
for tag, path in [("UKQ", "fixtures/rules_uk.json"), ("USQ", "fixtures/rules_us.json")]:
    rb = json.load(open(path))
    q = [{"clause_id": c["id"], "title": c["title"],
          "query": f"{c['id']} | {c['title']} | {c['requirement']}",
          "quantity": c.get("quantity"), "limit": c.get("limit"),
          "expected": c.get("expected")}
         for c in rb["clauses"]]
    print(f'export {tag}={base64.b64encode(json.dumps(q).encode()).decode()}')
PY
source /tmp/flwr_demo_env.sh
echo "UKQ and USQ exported (${#UKQ} and ${#USQ} chars)"
echo
echo "For \$LED, run the UK assessment first and keep its ledger:"
echo '  cd manufacturer-agent'
echo '  uv run flwr run . supergrid --stream --run-config \'
echo '    "agent.technical-file=\"mfr_northwind\" agent.jurisdiction=\"UK\" agent.queries-b64=\"$UKQ\"" \'
echo "    | python3 -c \"import sys,json;t=sys.stdin.read();i,j=t.find('{'),t.rfind('}');print(json.loads(t[i:j+1])['ledger_state_b64'])\" > /tmp/led.txt"
echo '  export LED=$(cat /tmp/led.txt)'
