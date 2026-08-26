# Minimum-disclosure conformity assessment

Cross-organisation compliance checking with Flower Agents, where the
manufacturer's technical file never leaves the manufacturer.

## The problem

A device is imported into the UK. Somebody has to establish that it complies
with national requirements. Today that means the manufacturer sends a technical
file — schematics, bill of materials, test reports — to an importer or approved
body, who reads it.

Manufacturers do not want to send it. It contains their suppliers, their costs,
their design. So the process stalls, or it proceeds on partial information, and
either way it takes weeks.

The same device sold in two markets goes through this twice, against two
different rulebooks, with two different parties reading the same secrets.

## What this does

Each party runs its own agent in its own Flower federation.

```
  Manufacturer A            Manufacturer B          <- own federation, own technical file
   agent (private)           agent (private)
        \                        /
         \   typed claims only  /
          \                    /
        UK agent          US agent                  <- one per rulebook, public rules
             \               /
              coordinator                           <- composes, never sees evidence
```

The regulator's agent decomposes its own rulebook into clauses and asks. The
manufacturer's agent answers from the technical file and returns a **compliance
matrix**: one row per clause, yes / no / not established, plus the report
reference it rests on. Nothing else crosses.

## Why it is not a prompt

Three layers, in order. The third is the point.

**1. The model never sees the secrets.** `disclosable_view()` strips the
confidential block before anything reaches the model context. It cannot
disclose what it was not shown.

**2. A typed egress contract.** Every outgoing claim is validated: fixed
fields, a 200-character note, and a check that no string from the confidential
block appears. Extra fields, over-long notes, bad statuses and supplier names
are all rejected.

**3. A disclosure ledger.** This is the part a prompt cannot do.

Individually safe answers are jointly disclosive. If the UK assessment learns
the radiated emission at 10 m, and the US assessment then learns it at 3 m, the
pair determines the antenna's departure from free-space falloff — its radiation
efficiency — to within 0.4 dB. No clause asked for that. It is competitively
valuable. And it is invisible to any check that looks at one answer at a time.

The ledger prices every answer in bits against everything already released,
**including releases made to a different regulator, in a different
jurisdiction, on a different day**, and refuses or downgrades:

```
US-EMC-1  FAIL   measured=None
  note: The 3 m measurement exceeds the Class B limit by 3.1 dB.
        Value withheld: with UK-EMC-1/UK it would pin antenna_efficiency_dB
        to +-0.4 dB.
```

The regulator still gets its verdict. Enforcement is unaffected. The secret
survives.

### Minimum sufficient disclosure

A threshold clause asks whether a quantity sits on one side of a published
limit. That is **one bit**. The measured value is more than the regulation
requires, so it is not released by default; a regulator must escalate to ask
for it, and the ledger then prices that request and may still refuse.

Measured on the fixtures here: eight clauses across two jurisdictions resolve
on **2 bits** under the default, against **11.23 bits** when both regulators
demand values — and against a technical file of tens of kilobytes.

## Layout

```
schema.py                     the egress contract
ledger.py                     disclosure accounting, differencing, budget
manufacturer-agent/           AgentApp: answers clauses from a private file
jurisdiction-agent/           AgentApp: decomposes a rulebook, adjudicates claims
run_assessment.py             coordinator: fan-out, threads the ledger
fixtures/                     two rulebooks, two technical files
```

`schema.py` and `ledger.py` are vendored into each app because a Flower App
Bundle ships its own dependencies.

## Running it

```bash
uv run flwr login supergrid

# one manufacturer, one jurisdiction
python3 run_assessment.py --jurisdictions uk --manufacturers northwind

# everything, and let regulators demand measured values
python3 run_assessment.py --request-exact
```

Per-assessment compliance matrices are written to `matrix_<mfr>_<jurisdiction>.csv`.

## Notes on the Flower APIs

- Built against `flwr 1.35.0`, using the `AgentSession` + OpenAI SDK pattern
  from `hub/apps/agent`, with every step reported through `agent.events.emit()`.
- The ledger is written to `context.state` so a reused run series keeps its
  memory. It is *also* threaded through run config by the coordinator, because
  `flwr run` has no way to join an existing run series from the CLI — each
  invocation starts a new one. Cross-assessment memory therefore has to be
  carried explicitly. That looks like a gap worth closing in the agent
  infrastructure.
