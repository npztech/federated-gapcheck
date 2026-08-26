"""
The UKRP-side coordinator.

Today this calls each node in-process, so the demo runs on one laptop.
Tomorrow, replace _dispatch() with a SuperGrid call and nothing else
in this file needs to change.

The coordinator never touches the nodes/ folders. Its only input is the
findings payload each node chooses to return.
"""

import json
from pathlib import Path

from checklist import CHECKLIST
from local_agent import run_gap_check

ROOT = Path(__file__).parent.parent
NODES = {
    "manufacturer_a": "Ningbo - infusion sets",
    "manufacturer_b": "Shenzhen - clinical thermometers",
    "manufacturer_c": "Guangzhou - orthopaedic supports",
}


def _dispatch(node_id: str) -> dict:
    """
    Send the checklist to one node and receive its findings.

    SWAP POINT: this is the function that becomes a SuperGrid dispatch.
    The signature stays the same - a node id in, a findings dict out.
    """
    return run_gap_check(node_id, ROOT / "nodes" / node_id)


def collect() -> list[dict]:
    results = []
    for node_id in NODES:
        payload = _dispatch(node_id)
        payload["display_name"] = NODES[node_id]
        results.append(payload)
    return results


def readiness(payload: dict) -> int:
    """A single 0-100 score, so the dashboard can rank nodes."""
    s = payload["summary"]
    total = len(CHECKLIST)
    return round(100 * (s["present"] + 0.5 * s["incomplete"]) / total)


def build_dashboard(results: list[dict]) -> str:
    rows = []
    for r in results:
        cells = []
        for f in r["findings"]:
            cls = {"present": "ok", "incomplete": "warn", "missing": "gap"}[f["status"]]
            label = {"present": "\u2713", "incomplete": "!", "missing": "\u2715"}[f["status"]]
            title = f'{f["id"]} {f["requirement"]} \u2014 {f["finding"]}'
            cells.append(f'<td class="{cls}" title="{title}">{label}</td>')
        score = readiness(r)
        bar = "ready" if score >= 90 else ("near" if score >= 60 else "far")
        rows.append(f"""<tr>
<th scope="row"><span class="nm">{r["node_id"].replace("_", " ")}</span>
<span class="sub">{r["display_name"]}</span></th>
{"".join(cells)}
<td class="score"><span class="{bar}">{score}</span></td></tr>""")

    heads = "".join(f'<th scope="col" title="{i["name_en"]}">{i["id"]}</th>' for i in CHECKLIST)
    transferred = sum(r["documents_transmitted"] for r in results)
    inspected = sum(r["documents_inspected"] for r in results)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UKRP readiness \u2014 federated gap check</title>
<style>
:root {{ --ink:#12212e; --mute:#5b6b78; --line:#dce3e8; --paper:#f7f9fa;
--ok:#1d7a5f; --warn:#b8791a; --gap:#b03636; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:40px 24px; background:var(--paper); color:var(--ink);
font:15px/1.6 "Segoe UI",-apple-system,system-ui,sans-serif; }}
.wrap {{ max-width:960px; margin:0 auto; }}
h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; letter-spacing:-.2px; }}
.lede {{ color:var(--mute); margin:0 0 28px; font-size:14px; }}
.stat {{ display:flex; gap:32px; padding:16px 20px; background:#fff;
border:1px solid var(--line); border-radius:10px; margin-bottom:24px; }}
.stat div span {{ display:block; }}
.stat .n {{ font-size:24px; font-weight:600; letter-spacing:-.5px; }}
.stat .k {{ font-size:12px; color:var(--mute); text-transform:uppercase;
letter-spacing:.6px; }}
.stat .zero .n {{ color:var(--ok); }}
table {{ width:100%; border-collapse:collapse; background:#fff;
border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
th,td {{ padding:10px 6px; text-align:center; font-size:13px; }}
thead th {{ background:#eef2f4; color:var(--mute); font-weight:500;
font-size:11px; border-bottom:1px solid var(--line); cursor:help; }}
tbody th {{ text-align:left; padding-left:16px; font-weight:500;
border-bottom:1px solid var(--line); }}
tbody td {{ border-bottom:1px solid var(--line); cursor:help; }}
.nm {{ display:block; text-transform:capitalize; }}
.sub {{ display:block; font-size:11px; color:var(--mute); font-weight:400; }}
.ok {{ color:var(--ok); background:rgba(29,122,95,.07); font-weight:600; }}
.warn {{ color:var(--warn); background:rgba(184,121,26,.09); font-weight:600; }}
.gap {{ color:var(--gap); background:rgba(176,54,54,.07); font-weight:600; }}
.score span {{ display:inline-block; min-width:38px; padding:2px 6px;
border-radius:4px; font-weight:600; font-size:12px; }}
.ready {{ background:rgba(29,122,95,.12); color:var(--ok); }}
.near {{ background:rgba(184,121,26,.14); color:var(--warn); }}
.far {{ background:rgba(176,54,54,.1); color:var(--gap); }}
.key {{ margin-top:18px; font-size:12px; color:var(--mute); }}
.key b {{ font-weight:600; }}
</style></head><body><div class="wrap">
<h1>UKRP readiness</h1>
<p class="lede">Three manufacturers assessed against the same GB Class&nbsp;IIa
checklist. Hover any cell for the finding.</p>
<div class="stat">
<div><span class="n">{len(results)}</span><span class="k">nodes</span></div>
<div><span class="n">{inspected}</span><span class="k">documents inspected</span></div>
<div class="zero"><span class="n">{transferred}</span><span class="k">documents transferred</span></div>
</div>
<table><thead><tr><th scope="col">Manufacturer</th>{heads}
<th scope="col">Ready</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<p class="key"><b>\u2713</b> present &nbsp; <b>!</b> present but incomplete
&nbsp; <b>\u2715</b> missing. Every assessment was performed on the
manufacturer's own machine. The coordinator received findings only.</p>
</div></body></html>"""


if __name__ == "__main__":
    results = collect()

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "findings.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "dashboard.html").write_text(build_dashboard(results), encoding="utf-8")

    print("Federated gap check complete.\n")
    for r in results:
        s = r["summary"]
        print(f'  {r["node_id"]:<16} '
              f'present {s["present"]:>2}  '
              f'incomplete {s["incomplete"]:>2}  '
              f'missing {s["missing"]:>2}   '
              f'readiness {readiness(r)}%')
    print(f"\n  documents inspected  : {sum(r['documents_inspected'] for r in results)}")
    print(f"  documents transferred: {sum(r['documents_transmitted'] for r in results)}")
    print(f"\nWritten to {out}/dashboard.html")
