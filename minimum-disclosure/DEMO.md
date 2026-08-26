# Demo script — 4 minutes

Two terminals. Left: the run. Right: `matrix_*.csv` open.

Before you start:
    cd ~/flower_hackathon/compliance/minimum-disclosure
    uv run --project manufacturer-agent flwr login supergrid   # already done
    python3 run_assessment.py                                   # pre-warmed, ~8 min

---

## 0:00 — the problem  (say it, don't show it)

"[Teammate] runs a company that does this every day. A device arrives at the UK
border. Somebody has to establish it complies. That means the manufacturer sends
their technical file — schematics, bill of materials, test reports — to a party
they don't control.

Manufacturers refuse. So it takes weeks, or it proceeds on partial information.
Sell into two markets and it happens twice, to two different parties, against two
different rulebooks."

## 0:40 — the architecture  (one slide, your hand-drawn diagram)

"Every party runs its own agent in its own Flower federation. Two manufacturers,
two jurisdictions. The rulebooks are public so the jurisdiction agents need no
isolation. The technical files are not, so the manufacturers do."

## 1:10 — run it live

    uv run flwr run . supergrid --stream \
      --run-config "agent.technical-file=\"mfr_northwind\" agent.jurisdiction=\"US\" agent.queries-b64=\"$USQ\" agent.ledger-b64=\"$LED\""

Point at the event stream. Then at the CSV:

    clause_id,requirement,compliant,evidence_ref,disclosure_bits
    US-EMC-1,"Radiated emissions, 30-88 MHz",NO,TR-4471 §3.2,1.0

"That file is the entire outward transfer. One row per clause, yes or no, and the
report it rests on. The technical file never moved."

## 2:00 — THE MOMENT  (this is the demo)

Read the note aloud, verbatim:

    Value withheld: with UK-EMC-1/UK it would pin antenna_efficiency_dB
    to +-0.4 dB.

"The US regulator asked for the 3 metre measurement. It didn't get it — because
this manufacturer already gave the 10 metre figure to the UK assessment, on a
different day, in a different federation. Those two numbers together determine
the antenna's radiation efficiency. No clause asked for that. It's their design.

And notice the verdict is still FAIL. Enforcement is untouched. Only the secret
survived.

No prompt can do this. It needs cumulative accounting across every regulator
this manufacturer has ever answered."

## 2:50 — the number

    8 clauses, 2 jurisdictions, resolved on 2 bits
    11.23 bits if both regulators demand values
    technical file: withheld entirely

"A threshold clause asks whether a number is under a limit. That's one bit. The
measured value is more than the regulation requires. Our first version leaked
9.23 bits answering a question that needed one."

## 3:20 — the 2x2

    Northwind (NW-500)   UK: granted    US: refused
    Halden   (HD-220)    UK: refused    US: granted

"Same devices, opposite verdicts. UK measures at 10 metres, the FCC at 3. The
divergence is real, and it's why you need one agent per rulebook."

## 3:50 — close

"Three layers. The model never sees the confidential block. A typed contract
validates every claim. And a disclosure ledger prices each answer in bits
against everything already released. The third one is the contribution."

---

## Q&A — the ones they will ask

**"Isn't this just a prompt with a JSON schema?"**
Layers 1 and 2 are, and they're table stakes. Layer 3 isn't: it needs memory of
what was released to a different regulator in a different jurisdiction, and it
refuses based on a physical relation between two quantities. Show the ledger.

**"Has this been done?"**
Multi-agent compliance checking is crowded — there's an ACM multi-agent RAG
framework, and Credo AI, OneTrust, Regology sell it. Zero-knowledge compliance
verification exists and is patented. Both assume one organisation runs all the
agents. Nobody does minimum-disclosure across a real trust boundary.

**"Why Flower?"**
Federations are the trust boundary — an agent bounded to one organisation's data
and permissions. LangGraph and CrewAI have no equivalent. And the ledger lives in
run-series state.

**"What's the guarantee?"**
There isn't a cryptographic one. It's enforced accounting plus an audited
channel, not a proof. Say that before they say it.

**"Where did the numbers come from?"**
Synthetic fixtures built from the real regs — EMC Regulations 2016, Radio
Equipment Regulations 2017, FCC Part 15 B and C. Ground truth known, so the
verdicts are checkable.

## If the live run dies

`assessment.json` and the four `matrix_*.csv` files are on disk from the
pre-warmed run. Show those. Never debug on stage.
