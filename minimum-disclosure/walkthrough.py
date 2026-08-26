#!/usr/bin/env python3
"""One narrated assessment, end to end, so you can watch what crosses.

    python3 walkthrough.py
"""
import base64, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
def rule(t): print(f"\n\033[1m{'='*68}\n{t}\n{'='*68}\033[0m")

def clauses(jur):
    rb = json.loads((ROOT / f"fixtures/rules_{jur}.json").read_text())
    return [{"clause_id": c["id"], "title": c["title"],
             "query": f"{c['id']} | {c['title']} | {c['requirement']}",
             "quantity": c.get("quantity"), "limit": c.get("limit"),
             "expected": c.get("expected")} for c in rb["clauses"]]

def run(jur, ledger="", exact=False):
    cfg = {"agent.technical-file": "mfr_northwind", "agent.jurisdiction": jur.upper(),
           "agent.queries-b64": base64.b64encode(json.dumps(clauses(jur)).encode()).decode()}
    if ledger:
        cfg["agent.ledger-b64"] = ledger
    if exact:
        cfg["agent.request-exact"] = "true"
    p = subprocess.run(
        ["uv", "run", "flwr", "run", ".", "supergrid", "--stream", "--run-config",
         " ".join(f'{k}="{v}"' for k, v in cfg.items())],
        cwd=ROOT / "manufacturer-agent", capture_output=True, text=True, timeout=600)
    t = p.stdout
    i, j = t.find("{"), t.rfind("}")
    return json.loads(t[i:j + 1])

# ---------------------------------------------------------------- 1
rule("1. WHAT THE MANUFACTURER HOLDS  (never leaves their federation)")
tf = json.loads((ROOT / "fixtures/mfr_northwind.json").read_text())
print(f"  {tf['manufacturer']} — {tf['device']}\n")
print("  CONFIDENTIAL — never enters the model context:")
for part in tf["_confidential"]["bill_of_materials"]:
    print(f"    {part['part']:<14} {part['supplier']:<28} £{part['unit_cost_gbp']}")
print(f"    firmware       {tf['_confidential']['firmware_repo']}")
print("\n  EVIDENCE — the model may read this, but it still does not leave:")
for q, es in tf["evidence"].items():
    for e in es:
        print(f"    {q:<32} {str(e['value']):<12} {e['report']:<14} commit {e['commit']}")

# ---------------------------------------------------------------- 2
rule("2. UK REGULATOR ASKS  (4 clauses from EMC 2016 / RER 2017 / EESR 2016)")
for c in clauses("uk"):
    lim = c["limit"]
    print(f"  {c['clause_id']:<10} {c['title']:<34} " +
          (f"limit {lim['value']} {lim['unit']} @{lim.get('distance_m','-')}m" if lim else f"expects {c['expected']}"))

# ---------------------------------------------------------------- 3
rule("3. UK ASSESSMENT RUNS ON SUPERGRID")
uk = run("uk")
print("  what crossed the boundary:\n")
print("  " + uk["csv"].replace("\n", "\n  "))
print(f"  ledger: {uk['ledger']['bits_disclosed_total']} bits spent, "
      f"{uk['ledger']['bits_remaining']} remaining")

# ---------------------------------------------------------------- 4
rule("4. US REGULATOR ASKS — DAYS LATER, DIFFERENT RULEBOOK")
print("  The ledger from the UK assessment travels with the manufacturer.\n")
us = run("us", ledger=uk["ledger_state_b64"])
print("  " + us["csv"].replace("\n", "\n  "))

# ---------------------------------------------------------------- 5
rule("5. THE LEDGER'S DECISIONS")
for d in uk["decisions"] + us["decisions"]:
    verdict = "released" if d.get("allowed") else "REFUSED"
    print(f"  {d['clause_id']:<10} {d['quantity']:<34} {verdict:<9} "
          f"{d.get('released','-'):<6} {d.get('reason')}")
    for e in d.get("exposes", []):
        via = ", ".join(f"{c['clause_id']}/{c['jurisdiction']}" for c in e["because_of"])
        print(f"{'':>12}would pin {e['derived']} to +-{e['residual_dB']} dB via {via}")

# ---------------------------------------------------------------- 6
rule("6. RESULT")
print(f"  UK  clauses answered: {len(uk['claims'])}   US clauses answered: {len(us['claims'])}")
print(f"  total disclosed     : {us['ledger']['bits_disclosed_total']} bits")
print(f"  technical file bytes: 0  (withheld: {len(json.dumps(tf))} bytes)")

# ---------------------------------------------------------------- 7
rule("7. WHAT IF THE REGULATORS INSIST ON THE NUMBERS?")
print("  Above, no exact value ever left, so there was nothing to difference.")
print("  Now both regulators escalate and demand measured values.\n")

uk_x = run("uk", exact=True)
v = [c.get("measured", {}).get("value") for c in uk_x["claims"] if c.get("measured")]
print(f"  UK escalates -> released {v}, costing {uk_x['ledger']['bits_disclosed_total']} bits\n")

us_x = run("us", ledger=uk_x["ledger_state_b64"], exact=True)
print("  US escalates, with the UK ledger in hand:\n")
for c in us_x["claims"]:
    if c["clause_id"] == "US-EMC-1":
        print(f"    {c['clause_id']}  {c['status']}  measured={c.get('measured')}")
        print(f"    note: {c['note']}\n")
for d in us_x["decisions"]:
    if not d.get("allowed"):
        print(f"    LEDGER REFUSED {d['quantity']}  reason={d['reason']}")
        for e in d.get("exposes", []):
            via = ", ".join(f"{c['clause_id']}/{c['jurisdiction']}" for c in e["because_of"])
            print(f"      would pin {e['derived']} to +-{e['residual_dB']} dB "
                  f"({e['bits_revealed']} bits) via {via}")
print(f"\n  escalated total: {us_x['ledger']['bits_disclosed_total']} bits "
      f"vs 3.0 under minimum disclosure")
