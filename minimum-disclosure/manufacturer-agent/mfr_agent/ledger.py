"""Disclosure ledger.

The manufacturer agent answers questions from several regulators over time.
Any single answer may be harmless; a sequence of them is not. This module does
the accounting that decides what may actually leave.

Three ideas:

  1. Every secret quantity starts with a prior interval. Each answer is a
     constraint that narrows it. The information released is the log-ratio of
     the interval widths, in bits.

  2. Answers are not all the same price. Confirming PASS against a published
     threshold costs one bit. Releasing the measured value costs everything.

  3. Quantities are related. Emissions at 3 m and at 10 m are linked by free
     space path loss, so releasing both pins down a third quantity - antenna
     efficiency - that no clause ever asked about. That is the differencing
     problem, and it is why per-answer checks are not enough.

The ledger persists across the whole run series, so a question asked by the US
assessment is priced against what the UK assessment already learned.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# Priors: what an outsider could reasonably assume before asking anything.
# --------------------------------------------------------------------------
PRIORS: dict[str, dict[str, float]] = {
    "radiated_emissions_30_230MHz@10": {"lo": 0.0, "hi": 60.0, "precision": 0.1},
    "radiated_emissions_30_230MHz@3":  {"lo": 0.0, "hi": 70.0, "precision": 0.1},
    "spurious_emissions":              {"lo": -80.0, "hi": 0.0, "precision": 0.5},
}

# Derived quantities an adversary can compute from combinations of the above.
# Each entry: the inputs, and the residual uncertainty in the derived value
# given exact knowledge of every input.
DERIVED: dict[str, dict[str, Any]] = {
    "antenna_efficiency_dB": {
        "inputs": [
            "radiated_emissions_30_230MHz@10",
            "radiated_emissions_30_230MHz@3",
        ],
        # Free space path loss between 3 m and 10 m is ~10.46 dB. Any departure
        # from that is the antenna's own behaviour.
        "prior_width": 12.0,
        "residual_when_known": 0.4,
        "note": "antenna efficiency, inferable from the 3 m / 10 m pair",
    },
}


def minimum_sufficient(clause: dict[str, Any]) -> str:
    """The cheapest answer that still resolves this clause.

    Manufacturers do not want to disclose anything. So the question is not
    "may we release the value" but "what is the least we can say and still
    let the regulator do its job".

    A threshold clause asks whether a quantity sits on one side of a published
    limit. That is one bit. The measured value is strictly more than the
    regulation requires, and releasing it is a choice, not an obligation.
    """
    if clause.get("limit"):
        return "bit"          # "is it under the limit?" -> yes or no
    if clause.get("expected"):
        return "bit"          # "does it match the named standard?" -> yes or no
    return "exact"            # nothing to compare against; the value is the answer


def _bits(prior_width: float, posterior_width: float) -> float:
    """Information released when an interval narrows, in bits."""
    if posterior_width <= 0:
        posterior_width = 1e-9
    if posterior_width >= prior_width:
        return 0.0
    return math.log2(prior_width / posterior_width)


@dataclass
class Disclosure:
    """One thing that was released about one quantity."""

    quantity: str
    kind: str          # "bit" | "interval" | "exact"
    bits: float
    clause_id: str
    jurisdiction: str


@dataclass
class Ledger:
    """Cumulative disclosure across the whole run series."""

    budget_bits: float = 12.0
    derived_floor_bits: float = 4.0
    disclosures: list[Disclosure] = field(default_factory=list)

    # ---- persistence -----------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(
            {
                "budget_bits": self.budget_bits,
                "derived_floor_bits": self.derived_floor_bits,
                "disclosures": [d.__dict__ for d in self.disclosures],
            }
        )

    @classmethod
    def from_json(cls, blob: str | None) -> "Ledger":
        if not blob:
            return cls()
        raw = json.loads(blob)
        led = cls(
            budget_bits=raw.get("budget_bits", 12.0),
            derived_floor_bits=raw.get("derived_floor_bits", 4.0),
        )
        led.disclosures = [Disclosure(**d) for d in raw.get("disclosures", [])]
        return led

    # ---- accounting ------------------------------------------------------
    def spent_on(self, quantity: str) -> float:
        return sum(d.bits for d in self.disclosures if d.quantity == quantity)

    def total_spent(self) -> float:
        return sum(d.bits for d in self.disclosures)

    def known_exactly(self) -> set[str]:
        return {d.quantity for d in self.disclosures if d.kind == "exact"}

    def price(self, quantity: str, kind: str) -> float:
        """What this answer would cost, in bits."""
        if kind == "bit":
            return 1.0
        prior = PRIORS.get(quantity)
        if prior is None:
            return 1.0
        width = prior["hi"] - prior["lo"]
        if kind == "exact":
            return _bits(width, prior["precision"])
        return _bits(width, width / 2.0)  # a one-sided interval halves it

    # ---- the differencing check -----------------------------------------
    def derived_exposure(self, quantity: str, kind: str) -> list[dict[str, Any]]:
        """Derived secrets that this answer would expose, with the inputs to blame."""
        if kind != "exact":
            return []
        would_know = self.known_exactly() | {quantity}
        exposed = []
        for name, spec in DERIVED.items():
            if not set(spec["inputs"]).issubset(would_know):
                continue
            revealed = _bits(spec["prior_width"], spec["residual_when_known"])
            if revealed >= self.derived_floor_bits:
                culprits = [
                    d for d in self.disclosures
                    if d.quantity in spec["inputs"] and d.kind == "exact"
                ]
                exposed.append(
                    {
                        "derived": name,
                        "note": spec["note"],
                        "bits_revealed": round(revealed, 2),
                        "residual_dB": spec["residual_when_known"],
                        "because_of": [
                            {"clause_id": c.clause_id, "jurisdiction": c.jurisdiction,
                             "quantity": c.quantity}
                            for c in culprits
                        ],
                    }
                )
        return exposed

    # ---- the decision ----------------------------------------------------
    def adjudicate(self, quantity: str, kind: str) -> dict[str, Any]:
        """May this answer be released? If not, what may be released instead?"""
        cost = self.price(quantity, kind)

        exposed = self.derived_exposure(quantity, kind)
        if exposed:
            return {
                "allowed": False,
                "downgrade_to": "bit",
                "cost_bits": cost,
                "reason": "differencing",
                "exposes": exposed,
            }

        # The budget is a total across every quantity: roughly, you may give
        # away one precise number, and after that you answer in bits.
        if self.total_spent() + cost > self.budget_bits:
            return {
                "allowed": False,
                "downgrade_to": "bit",
                "cost_bits": cost,
                "reason": "budget",
                "spent_total": round(self.total_spent(), 2),
                "budget_bits": self.budget_bits,
            }

        return {"allowed": True, "cost_bits": cost, "reason": "within budget"}

    def record(self, quantity: str, kind: str, clause_id: str, jurisdiction: str) -> float:
        cost = self.price(quantity, kind)
        self.disclosures.append(
            Disclosure(quantity, kind, cost, clause_id, jurisdiction)
        )
        return cost

    def summary(self) -> dict[str, Any]:
        per_quantity: dict[str, float] = {}
        for d in self.disclosures:
            per_quantity[d.quantity] = round(per_quantity.get(d.quantity, 0.0) + d.bits, 2)
        return {
            "answers_given": len(self.disclosures),
            "bits_disclosed_total": round(self.total_spent(), 2),
            "bits_by_quantity": per_quantity,
            "budget_bits": self.budget_bits,
            "bits_remaining": round(max(0.0, self.budget_bits - self.total_spent()), 2),
        }
