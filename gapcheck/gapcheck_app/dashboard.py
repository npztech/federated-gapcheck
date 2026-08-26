"""
Dashboard rendering for the coordinator.

Ported from agent/coordinator.py::build_dashboard() and extended with a
fourth cell state for `not_applicable`, which the single-process version
has no concept of. That module is deliberately left untouched as the
no-Flower fallback, so the two renderers now differ. If you change the
look here, decide whether the fallback needs the same change.

This module never sees document content. Its input is the findings
payload the nodes chose to return.
"""

from __future__ import annotations

from html import escape

from .gap_check import INCOMPLETE, MISSING, NOT_APPLICABLE, PRESENT, readiness

_CELL_CLASS = {
    PRESENT: "ok",
    INCOMPLETE: "warn",
    MISSING: "gap",
    NOT_APPLICABLE: "na",
}
_CELL_LABEL = {
    PRESENT: "✓",
    INCOMPLETE: "!",
    MISSING: "✕",
    NOT_APPLICABLE: "—",
}


def build_dashboard(results: list[dict], checklist: list[dict]) -> str:
    """Render the findings from every node as a single HTML page."""
    rows = []
    for r in results:
        by_id = {f["id"]: f for f in r["findings"]}
        cells = []
        for item in checklist:
            f = by_id.get(item["id"])
            if f is None:
                cells.append('<td class="na" title="Not reported">—</td>')
                continue
            cls = _CELL_CLASS.get(f["status"], "na")
            label = _CELL_LABEL.get(f["status"], "?")
            title = f'{f["id"]} {f["requirement"]} — {f["finding"]}'
            cells.append(f'<td class="{cls}" title="{escape(title, quote=True)}">{label}</td>')

        score = readiness(r)
        bar = "ready" if score >= 90 else ("near" if score >= 60 else "far")
        name = escape(str(r["node_id"]).replace("_", " "))
        sub = escape(str(r.get("agent_display") or r.get("display_name") or ""))
        rows.append(f"""<tr>
<th scope="row"><span class="nm">{name}</span>
<span class="sub">{sub}</span></th>
{"".join(cells)}
<td class="score"><span class="{bar}">{score}</span></td></tr>""")

    heads = "".join(
        f'<th scope="col" title="{escape(i["name_en"], quote=True)}">{i["id"]}</th>'
        for i in checklist
    )
    transferred = sum(r["documents_transmitted"] for r in results)
    inspected = sum(r["documents_inspected"] for r in results)
    na_total = sum(r["summary"].get(NOT_APPLICABLE, 0) for r in results)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UKRP readiness — federated gap check</title>
<style>
:root {{ --ink:#12212e; --mute:#5b6b78; --line:#dce3e8; --paper:#f7f9fa;
--ok:#1d7a5f; --warn:#b8791a; --gap:#b03636; --na:#8a97a1; }}
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
.na {{ color:var(--na); background:rgba(138,151,161,.10); font-weight:600; }}
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
checklist, each by the device agent its own node runs. Hover any cell for
the finding.</p>
<div class="stat">
<div><span class="n">{len(results)}</span><span class="k">nodes</span></div>
<div><span class="n">{inspected}</span><span class="k">documents inspected</span></div>
<div class="zero"><span class="n">{transferred}</span><span class="k">documents transferred</span></div>
<div><span class="n">{na_total}</span><span class="k">not applicable</span></div>
</div>
<table><thead><tr><th scope="col">Manufacturer</th>{heads}
<th scope="col">Ready</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<p class="key"><b>✓</b> present &nbsp; <b>!</b> present but incomplete
&nbsp; <b>✕</b> missing &nbsp; <b>—</b> not applicable to this
device. Readiness excludes requirements ruled not applicable. Every
assessment was performed on the manufacturer's own machine. The
coordinator received findings only.</p>
</div></body></html>"""
