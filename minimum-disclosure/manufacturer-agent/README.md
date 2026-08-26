# Manufacturer Agent

Answers a regulator's conformity questions from a device technical file, and
releases as little as possible while doing it.

You run this in **your own** Flower federation. It reads your technical file,
and the only thing that leaves is a compliance matrix: one row per clause,
yes / no / not established, plus the report reference the answer rests on.

## Why it refuses things

A single answer is rarely disclosive. A sequence is.

If a UK assessment learns your radiated emission at 10 m, and a US assessment
then learns it at 3 m, the pair determines your antenna's departure from
free-space falloff — its radiation efficiency — to within a fraction of a dB.
No clause asked for that. It is your design.

So this agent keeps a **disclosure ledger**, priced in bits, that spans every
regulator you have ever answered. Before any value leaves, the ledger checks
it against everything already released and refuses or downgrades:

```
US-EMC-1  FAIL  measured=None
  note: The [redacted] m measurement exceeds the Class B limit by [redacted] dB.
        Value withheld: with UK-EMC-1/UK it would pin antenna_efficiency_dB
        to +[redacted] dB.
```

The regulator still gets its verdict. Only the number is withheld.

## Minimum sufficient disclosure

A threshold clause asks whether a quantity sits under a published limit. That
is **one bit**. The measured value is more than the regulation requires, so it
is not released by default; a regulator must escalate to ask for it, and the
ledger prices that request and may still refuse.

Eight clauses across two jurisdictions resolve on **2 bits**.

## Three layers, independently enforced

1. **The model never sees your secrets.** The confidential section of the
   technical file is stripped before anything reaches the model context.
2. **A typed egress contract.** Fixed fields, a bounded note, and rejection of
   any string drawn from the confidential section. When a value is withheld, no
   digits may leave, because a margin reconstructs the number.
3. **The disclosure ledger**, above.

## Run it

```bash
flwr new @alpozaydin/manufacturer-agent
cd manufacturer-agent && uv sync

flwr run . supergrid --federation @your/federation --stream \
  --run-config "agent.jurisdiction=\"UK\" \
                agent.technical-file-b64=\"<your file, base64 JSON>\" \
                agent.queries-b64=\"<clauses from the jurisdiction agent>\""
```

| config | meaning |
|---|---|
| `agent.technical-file-b64` | your technical file. Supply your own; the bundled fixtures are demo data |
| `agent.queries-b64` | clause queries from a jurisdiction agent |
| `agent.ledger-b64` | disclosure ledger carried from a previous assessment |
| `agent.request-exact` | regulator escalates and asks for measured values |
| `agent.input` | a plain question. No clause limit means no priced disclosure, so no value is released |

## Read it before you run it

```bash
ssh-keygen -t ed25519 -f ~/.flwr/signing_key -N ""   # must have no passphrase
flwr app review @alpozaydin/manufacturer-agent
```

Unpacks this agent so you can read every line of the code that is about to
touch your technical file, then signs your review to Flower Hub.

## What this does not do

The agent executes on SuperGrid, so your technical file reaches the platform.
It never reaches the other manufacturer, and it never reaches the regulator —
those are enforced. Keeping the file on your own hardware is the SuperNode
deployment, and it is not built here.

There is no cryptographic guarantee. This is enforced accounting over an
audited channel.

## The set

| app | role |
|---|---|
| [`@npztech/gapcheck`](https://flower.ai/apps/npztech/gapcheck) | UK MDR document gap check, three device agent profiles, file stays on the node |
| [`@alpozaydin/manufacturer-agent`](https://flower.ai/apps/alpozaydin/manufacturer-agent) | answers clause queries, disclosure ledger |
| [`@alpozaydin/jurisdiction-agent`](https://flower.ai/apps/alpozaydin/jurisdiction-agent) | decomposes a rulebook, adjudicates claims |
| [`@alpozaydin/local-node`](https://flower.ai/apps/alpozaydin/local-node) | ledger enforced on the manufacturer's own machine |

Built at the Collaborative Agent Hackathon, Cambridge, 26 August 2026.
