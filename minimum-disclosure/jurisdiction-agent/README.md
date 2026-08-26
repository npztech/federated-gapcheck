# Jurisdiction Agent

Holds one national rulebook. Turns it into clause queries, then rules on the
claims manufacturers return.

It never sees a technical file. It only ever sees claims that already passed a
manufacturer's egress contract.

## Two modes

**Decompose** — given no claims, it emits one query per clause, carrying the
quantity and the limit including test distance so the manufacturer's ledger can
price the answer before releasing it.

**Adjudicate** — given claims, it rules per clause and issues a market-access
decision: `GRANTED`, `REFUSED`, or `BLOCKED_PENDING_EVIDENCE`.

## The rule that matters

A claim of PASS against a published limit, carrying an evidence reference, is
sufficient on its own. `"measured": null` is normal and expected — a
manufacturer is not obliged to disclose the measured value, and a clause is
**not** marked insufficient merely because the number was withheld.

Judge the assertion, not the disclosure. Without that rule, minimum disclosure
would cost a manufacturer their market access, which defeats the point.

## Run it

```bash
flwr run . supergrid --stream --run-config 'agent.rulebook="uk"'
flwr run . supergrid --stream --run-config 'agent.rulebook="us" agent.claims-b64="<claims>"'
```

Ships with UK (EMC Regulations 2016, Radio Equipment Regulations 2017,
Electrical Equipment Safety Regulations 2016) and US (47 CFR Part 15 Subparts B
and C, FCC RF exposure, NRTL listing) for a mains-powered radio-enabled
consumer device.

Pairs with `@alpozaydin/manufacturer-agent`.
