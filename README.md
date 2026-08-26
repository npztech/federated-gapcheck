# Federated regulatory gap check

A UKRP sends a compliance checklist to overseas manufacturers. Each
manufacturer's agent reads their technical file locally and returns 
twelve findings. No document ever crosses the network. 

Built for the Collaborative Agent Hackathon, Cambridge, 26 August 2026.

---

## Run it

Federated, three SuperNodes on one laptop — this is the demo:

```
See run_local_demo.md
```

Single-process fallback, no Flower runtime required:

```
python make_synthetic_data.py
cd agent
python coordinator.py
```

Then open `out/dashboard.html`.

Expected output:

```
manufacturer_a   present 12  incomplete  0  missing  0   readiness 100%
manufacturer_b   present  7  incomplete  1  missing  4   readiness  62%
manufacturer_c   present  2  incomplete  5  missing  5   readiness  38%

documents inspected  : 26
documents transferred: 0
```

That last pair of numbers is the demo.

---

## Layout

```
nodes/manufacturer_a|b|c/   simulated local technical files (synthetic)
agent/checklist.py          the 12 requirements - the only thing sent out
agent/local_agent.py        node-side logic, single-process version
agent/coordinator.py        dispatch + aggregate + dashboard
gapcheck/                   the Flower app - ServerApp + ClientApp
run_local_demo.md           four-terminal federated setup
out/                        findings.json, dashboard.html
```

**Where Flower plugs in.** `coordinator._dispatch()` was the swap point,
and it has been swapped. `gapcheck/` is a standard Flower app: the
ServerApp distributes the checklist over a Grid, and a ClientApp runs the
same gap check inside each manufacturer's own SuperNode.

Not an AgentApp. An AgentApp task is executed by the SuperLink, which has
no route to node data — `GetNodes` and `PushMessages` are refused for any
task that is not a ServerApp. Node-local data is reachable only by a
ClientApp, which reads its folder from `context.node_config["data-dir"]`,
a path set by the node operator and unreachable by the coordinator.

---

## The privacy property

This is the whole point, so it is worth stating precisely.

`_load_documents()` reads document text into memory. `_match()` evaluates
it. The text is then discarded. The returned payload contains a checklist
id, a status, and a finding note written by the agent — never a filename
of a missing document, never an excerpt, never the text.

`documents_transmitted` is hard-coded to 0 because it is structurally 0.
If you later add a code path that returns content, change that field
honestly or the demo is a lie.

---

## Status

**Tier 1 — done.** `agent/coordinator.py` runs the whole check in one
process. Kept as a fallback that needs no Flower runtime.

**Tier 2 — done. This is the demo.** `gapcheck/` runs the same check across
three real SuperNodes, each reading only its own `--node-config data-dir`.
Verified end to end on 26 August; the federated numbers are identical to
the single-process ones. See `run_local_demo.md`.

**Tier 3 — not attempted.** The natural next step is a model call inside
`_match()` for semantic judgement — *"does this DoC cite UK MDR 2002 or
EU MDR?"* — instead of keyword markers. It strengthens the story rather
than diluting it: the model runs on the node, so document text still never
leaves.

---

## Known limits

State these yourself before a judge finds them. Naming your own gaps
reads as competence.

- Keyword matching, not comprehension. Tier 3 fixes this.
- Applicability is not inferred. R05, R06 and R09 depend on device
  characteristics — sterile or not, body-contacting or not, class. The
  agent flags them for confirmation rather than guessing.
- Twelve requirements is a demo subset. A real Class IIa submission
  runs considerably longer.
- No authentication, no audit trail, no signing. A production version
  needs all three.

## Data

Every document under `nodes/` is fabricated. Do not put real client
technical files in this repository.
