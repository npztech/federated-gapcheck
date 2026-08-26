# gapcheck

A federated regulatory gap check for medical device manufacturers.

A UK Responsible Person sends the same compliance checklist to every
manufacturer they represent. Each manufacturer's node reads its own
technical file locally and returns a status per requirement. **No document
ever crosses the network.**

Built at the Collaborative Agent Hackathon, Cambridge, 26 August 2026.

---

## The problem

A UKRP is legally accountable for the technical files of manufacturers they
have never audited, often overseas. The files are commercially sensitive and
frequently incomplete. Today the UKRP either asks for the whole file — which
manufacturers resist, and which creates a custody problem — or takes their
word for it.

Neither is good enough. What the UKRP actually needs is a much smaller
answer: *which of the twelve required documents exist, and are they usable?*

## The shape of the answer

```
manufacturer_a   present 12  incomplete  0  missing  0   readiness 100%
manufacturer_b   present  7  incomplete  1  missing  4   readiness  62%
manufacturer_c   present  2  incomplete  5  missing  5   readiness  38%

documents inspected  : 26
documents transferred: 0
```

That last pair of numbers is the point. Twenty-six documents were read.
Zero were sent.

---

## How it works

**ServerApp** (coordinator side) serialises the checklist — twelve GB Class
IIa requirements under the Medical Devices Regulations 2002 — and sends one
`query.gap_check` message to every connected SuperNode. It has no knowledge
of which manufacturers exist until they reply.

**ClientApp** (manufacturer side) runs on the manufacturer's own machine.
It reads `context.node_config["data-dir"]`, a path chosen by the node
operator and unreachable by the coordinator. It evaluates each document
against the checklist it was handed and returns findings.

The checklist is the only payload that travels outward. The findings are
the only payload that travels back.

## The privacy property, precisely

This is the whole claim, so it is worth stating exactly.

`gap_check.run_gap_check()` reads document text into memory and evaluates
it. The text goes out of scope when the function returns. The dict it
returns contains, per checklist item: an id, a requirement name, a status
of `present` / `incomplete` / `missing`, and a finding note drawn from a
fixed set of sentences.

It does not contain document text. It does not contain excerpts. It does
not contain filenames — not even for the documents reported as missing.

`documents_transmitted` is hard-coded to `0` because it is structurally
zero: there is no code path in that module that places document content in
the return value. If someone later adds one, that field must change
honestly or the claim becomes a lie.

You can verify the boundary yourself. Build the app and list the archive —
it contains five Python files and nothing else. No manufacturer data is
packaged, because none of it is the coordinator's to package.

```bash
flwr build --app .
```

---

## Configuration

Set on each SuperNode, by its operator, at startup:

| key | required | meaning |
|---|---|---|
| `data-dir` | yes | absolute path to that manufacturer's technical file |
| `node-name` | no | identifier in the report; defaults to the folder name |
| `display-name` | no | human label, e.g. `"Ningbo - infusion sets"` |

```bash
flower-supernode --superlink <host>:9092 --node-config 'data-dir="/abs/path" node-name="manufacturer_a"'
```

Set on the run, by the coordinator:

| key | default | meaning |
|---|---|---|
| `checklist-version` | `GB-CLASS-IIa-v1` | rubric version announced to nodes |
| `round-timeout` | `120.0` | seconds to wait for all nodes |
| `output-dir` | repo `out/` | absolute path for `findings.json`; empty to skip |

A node started without `data-dir` returns an explicit error rather than
reporting an empty folder as twelve gaps.

---

## Known limits

Stated here rather than left for a reader to find.

- **Keyword matching, not comprehension.** A document is judged by keywords
  in its filename and opening lines, and by markers such as "draft" or a
  citation of EU MDR where UK MDR 2002 is required. It does not read for
  meaning. The natural next step is a model call inside the matcher —
  which, because it would run on the node, preserves the privacy property.
- **Applicability is not inferred.** Requirements R05, R06 and R09 depend
  on device characteristics — sterile or not, body-contacting or not,
  risk class. The agent flags these for confirmation rather than guessing.
- **Twelve requirements is a demo subset.** A real Class IIa submission is
  considerably longer.
- **No authentication, no audit trail, no signing** in this build. A
  production deployment needs all three, and Flower supports node
  authentication for the first.

## Running it

See `run_local_demo.md` in the project repository for a four-terminal local
setup with three simulated manufacturers.

## Data

All manufacturer documents in the demo are synthetic. Do not place real
client technical files in a repository.
