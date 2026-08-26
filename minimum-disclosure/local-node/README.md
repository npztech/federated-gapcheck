# Local Node Conformity

Conformity assessment where the technical file never leaves the manufacturer's
machine.

A `ServerApp` sends a public rulebook. A `ClientApp` runs inside the
manufacturer's own SuperNode, reads a folder **the node operator chose**, and
returns claims. The coordinator cannot see the folder and cannot change the path.

```
Dispatching 4 clauses of UK to 1 manufacturer node(s)...

  Northwind Acoustics Ltd
    UK-EMC-1   PASS   measured=None   TR-4471 §3.1
    UK-RED-1   PASS   measured=None   TR-4472 §2.4
    UK-SAFE-1  PASS   measured=None   SAF-1180
    UK-MARK-1  PASS   measured=None   DOC-NW500-UK
    ledger: 2.0 bits

  documents transmitted: 0
```

## What is different here

The egress contract and the disclosure ledger run **on the manufacturer's
side**, so the boundary is enforced before anything reaches the network rather
than after.

`measured=None` is deliberate. A threshold clause asks which side of a
published limit a quantity sits on — that is one bit. The measured value is
more than the regulation requires, so it is not released.

The ledger also prices answers against everything already disclosed, including
to a different regulator on a different day. Releasing an emission figure at
10 m and again at 3 m would pin the antenna's radiation efficiency to a
fraction of a dB, which no clause asked for. The ledger refuses the second one.

## Run it

Three terminals.

```bash
# 1 — SuperLink
flower-superlink --insecure

# 2 — the manufacturer's node
flower-supernode --insecure --superlink 127.0.0.1:9092 \
  --host 127.0.0.1 --port 9094 \
  --node-config 'data-dir="/path/to/your/files"'

# 3 — the regulator
flwr run . localdev --stream --run-config 'rulebook="uk"'
```

`data-dir` holds a `technical_file.json`. Swap `rulebook="us"` for FCC rules.

## Why there is no model in this one

A `ClientApp` cannot call the model API — node-facing Runtime endpoints are
gated to `TaskType.SERVER_APP`. So clause matching here is deterministic. That
is a property, not a gap: **the component that touches the secrets has no model
in it.**

Language reasoning lives in the agent apps instead.

## The set

| app | role |
|---|---|
| [`@npztech/gapcheck`](https://flower.ai/apps/npztech/gapcheck) | UK MDR document gap check, three device agent profiles |
| [`@alpozaydin/manufacturer-agent`](https://flower.ai/apps/alpozaydin/manufacturer-agent) | answers clause queries, disclosure ledger |
| [`@alpozaydin/jurisdiction-agent`](https://flower.ai/apps/alpozaydin/jurisdiction-agent) | decomposes a rulebook, adjudicates claims |
| `@alpozaydin/local-node` | this one — the file never moves |

Built at the Collaborative Agent Hackathon, Cambridge, 26 August 2026.
