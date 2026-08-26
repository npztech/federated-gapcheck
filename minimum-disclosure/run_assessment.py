#!/usr/bin/env python3
"""Coordinator.

Drives a cross-organisation conformity assessment:

    for each jurisdiction:            decompose its rulebook into clause queries
      for each manufacturer:          ask that manufacturer's agent, in its own
                                      federation, one clause at a time
    for each (jurisdiction, mfr):     adjudicate the collected claims

The manufacturers' technical files never leave their federations. Only claims
that passed the egress contract cross, and this script counts every byte.

Usage:
    python run_assessment.py --dry-run          # show the plan, run nothing
    python run_assessment.py --jurisdictions uk --manufacturers northwind
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# Each manufacturer runs in its own account's federation. Fill these in with
# your teammates' federations, e.g. "@teammate/workspace".
MANUFACTURERS = {
    "northwind": {
        "technical_file": "mfr_northwind",
        "federation": None,          # None -> the default federation of this account
        "label": "Northwind Acoustics (NW-500)",
    },
    "halden": {
        "technical_file": "mfr_halden",
        "federation": None,
        "label": "Halden Devices (HD-220)",
    },
}



def extract_json(text: str) -> dict:
    """Pull the last complete JSON object out of a run's log stream."""
    depth, start, best = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                best = parsed
    if best is None:
        raise RuntimeError("no JSON object found in run output")
    return best


def b64(payload: str) -> str:
    """Config values travel base64-encoded: TOML cannot carry raw JSON safely."""
    return base64.b64encode(payload.encode()).decode()


def toml_escape(value: str) -> str:
    """Escape a value for a double-quoted TOML string in --run-config."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def flwr_run(app_dir: str, config: dict[str, str], federation: str | None) -> dict:
    """Run one AgentApp and return the JSON it printed."""
    cfg = " ".join(f'{k}="{toml_escape(str(v))}"' for k, v in config.items())
    cmd = ["uv", "run", "flwr", "run", ".", "supergrid", "--stream", "--run-config", cfg]
    if federation:
        cmd += ["--federation", federation]
    proc = subprocess.run(
        cmd, cwd=ROOT / app_dir, capture_output=True, text=True, timeout=600
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{app_dir} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return extract_json(proc.stdout)


def assess(jurisdiction: str, mfr_key: str, ledger_b64: str = "",
           request_exact: bool = False, verbose: bool = True) -> dict:
    mfr = MANUFACTURERS[mfr_key]

    if verbose:
        print(f"\n=== {mfr['label']}  ->  {jurisdiction.upper()} ===", flush=True)

    # 1. the jurisdiction agent decomposes its own rulebook
    plan = flwr_run("jurisdiction-agent", {"agent.rulebook": jurisdiction}, None)
    queries = plan["queries"]
    if verbose:
        print(f"  {len(queries)} clauses to check", flush=True)

    # 2. the manufacturer's agent answers all clauses at once, in its own federation
    config = {
        "agent.technical-file": mfr["technical_file"],
        "agent.jurisdiction": jurisdiction.upper(),
        "agent.queries-b64": b64(json.dumps(queries)),
    }
    if ledger_b64:
        config["agent.ledger-b64"] = ledger_b64
    if request_exact:
        config["agent.request-exact"] = "true"

    result = flwr_run("manufacturer-agent", config, mfr["federation"])
    claims = result["claims"]
    egress_bytes = result["egress"]["bytes_crossed"]
    if verbose:
        for c in claims:
            print(f"    {c['clause_id']:<10} {c['status']:<12} {c.get('evidence_ref') or '-'}", flush=True)

    # 3. the jurisdiction agent rules on the claims
    report = flwr_run(
        "jurisdiction-agent",
        {"agent.rulebook": jurisdiction, "agent.claims-b64": b64(json.dumps(claims))},
        None,
    )
    # ---- round 2: the jurisdiction agent's follow-ups go back ------------
    # Adjudication produces specific questions when evidence is insufficient.
    # Delivering them is what makes this an exchange rather than a pipeline.
    followups = [c for c in report.get("clauses", []) if c.get("followup")]
    if followups:
        by_id = {q["clause_id"]: q for q in queries}
        if verbose:
            print(f"  {len(followups)} follow-up question(s) -> manufacturer", flush=True)
        second = flwr_run(
            "manufacturer-agent",
            {
                "agent.technical-file": mfr["technical_file"],
                "agent.jurisdiction": jurisdiction.upper(),
                "agent.queries-b64": b64(json.dumps([
                    {**by_id.get(c["clause_id"], {"clause_id": c["clause_id"]}),
                     "query": f"{c['clause_id']} | follow-up | {c['followup']}"}
                    for c in followups])),
                "agent.ledger-b64": result["ledger_state_b64"],
            },
            mfr["federation"],
        )
        answered = {c["clause_id"]: c for c in second["claims"]}
        for c in claims:
            if c["clause_id"] in answered:
                c.update(answered[c["clause_id"]])
        egress_bytes += second["egress"]["bytes_crossed"]
        result["ledger_state_b64"] = second["ledger_state_b64"]
        result["ledger"] = second["ledger"]
        if verbose:
            for c in second["claims"]:
                print(f"    re-answered {c['clause_id']:<10} {c['status']}", flush=True)

        report = flwr_run(
            "jurisdiction-agent",
            {"agent.rulebook": jurisdiction, "agent.claims-b64": b64(json.dumps(claims))},
            None,
        )
        report.setdefault("jurisdiction", jurisdiction.upper())
        if verbose:
            print(f"  -> re-adjudicated: {report.get('market_access')}", flush=True)

    report["_rounds"] = 2 if followups else 1
    report["_followups"] = len(followups)
    report["_egress"] = {
        "claims_crossed": len(claims),
        "bytes_crossed": egress_bytes,
        "raw_technical_file_bytes_crossed": 0,
    }
    report["_ledger"] = result["ledger"]
    report["_ledger_state_b64"] = result["ledger_state_b64"]
    report["_csv"] = result["csv"]
    report["_withheld"] = [d for d in result["decisions"] if not d.get("allowed")]
    if verbose:
        print(f"  -> market access: {report.get('market_access')}", flush=True)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jurisdictions", default="uk,us")
    ap.add_argument("--manufacturers", default="northwind,halden")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--request-exact", action="store_true",
                    help="regulators demand measured values rather than yes/no")
    ap.add_argument("--out", default="assessment.json")
    args = ap.parse_args()

    jurisdictions = [j.strip() for j in args.jurisdictions.split(",") if j.strip()]
    mfrs = [m.strip() for m in args.manufacturers.split(",") if m.strip()]

    if args.dry_run:
        print("plan:")
        for m in mfrs:
            for j in jurisdictions:
                fed = MANUFACTURERS[m]["federation"] or "(default federation)"
                print(f"  {MANUFACTURERS[m]['label']:<32} x {j.upper():<3}  mfr agent in {fed}")
        return

    # The ledger follows the manufacturer, not the jurisdiction: what the UK
    # assessment learned is priced into what the US assessment may learn.
    results = {}
    for m in mfrs:
        ledger_b64 = ""
        for j in jurisdictions:
            report = assess(j, m, ledger_b64=ledger_b64, request_exact=args.request_exact)
            ledger_b64 = report["_ledger_state_b64"]
            results[f"{m}/{j}"] = report
            Path(f"matrix_{m}_{j}.csv").write_text(report["_csv"])

    Path(args.out).write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 64)
    print(f"{'manufacturer':<32} {'UK':<26} {'US':<26}")
    print("-" * 64)
    for m in mfrs:
        row = f"{MANUFACTURERS[m]['label']:<32} "
        for j in jurisdictions:
            row += f"{results[f'{m}/{j}'].get('market_access', '?'):<26} "
        print(row)
    print("-" * 64)
    for m in mfrs:
        last = results[f"{m}/{jurisdictions[-1]}"]
        led = last["_ledger"]
        print(f"  {MANUFACTURERS[m]['label']:<32} disclosed {led['bits_disclosed_total']:>6} bits"
              f"  ({led['bits_remaining']} of {led['budget_bits']} left)")
        for w in [w for j in jurisdictions for w in results[f"{m}/{j}"]["_withheld"]]:
            print(f"      withheld {w['quantity']} ({w['reason']})")
    tf_bytes = sum(len(json.dumps(json.loads(
        (ROOT / "fixtures" / f"{MANUFACTURERS[m]['technical_file']}.json").read_text()))) for m in mfrs)
    total = sum(r["_egress"]["bytes_crossed"] for r in results.values())
    print("-" * 64)
    print(f"claims crossed: {sum(r['_egress']['claims_crossed'] for r in results.values())}"
          f" | bytes crossed: {total} | technical file bytes crossed: 0"
          f" | technical files withheld: {tf_bytes} bytes")
    print("per-assessment CSVs written: " + ", ".join(f"matrix_{m}_{j}.csv" for m in mfrs for j in jurisdictions))
    print(f"\nfull report written to {args.out}")


if __name__ == "__main__":
    sys.exit(main())
