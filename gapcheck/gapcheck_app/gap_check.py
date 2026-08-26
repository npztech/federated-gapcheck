"""
The node-side gap check. This runs inside the ClientApp, on the
manufacturer's own machine.

SOURCE OF TRUTH for the matching logic: ../../agent/local_agent.py
`_load_documents`, `_contains` and `_match` are a copy of that module's.
Two deliberate differences: the rubric arrives as an argument rather than
an import, because the coordinator sends it over the wire; and each
requirement is filtered through a device agent, which decides whether the
requirement applies to this device at all. If you edit the matching logic
in one place, edit it in both.

The single most important property of this module:

    document text is read into memory, evaluated, and discarded.
    It is never placed in the returned payload.

The return value is the only thing that crosses the network boundary, and
in this build that boundary is real - a different process on a different
machine, reached over gRPC.
"""

from __future__ import annotations

import re
from pathlib import Path

from .agents.base import DeviceAgent

PRESENT = "present"
INCOMPLETE = "incomplete"
MISSING = "missing"
NOT_APPLICABLE = "not_applicable"

#: Statuses that count towards a readiness score. `not_applicable` is
#: absent on purpose - see `readiness()`.
SCORED_STATUSES = (PRESENT, INCOMPLETE, MISSING)


def _load_documents(folder: Path) -> list[tuple[str, str]]:
    """Read every document in the local technical file. Stays local."""
    docs = []
    for path in sorted(folder.glob("*.md")):
        docs.append((path.name, path.read_text(encoding="utf-8").lower()))
    return docs


def _contains(keyword: str, haystack: str) -> bool:
    """
    Word-boundary match.

    Substring matching produces false positives that would discredit the
    whole demo - 'cer' inside 'certificate' would report a clinical
    evaluation report that does not exist.
    """
    return re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", haystack) is not None


def _match(
    item: dict,
    docs: list[tuple[str, str]],
    incomplete_markers: list[str],
    wrong_regulation_markers: list[str],
) -> tuple[str, str]:
    """
    Decide present / incomplete / missing for one checklist item.

    A document counts as addressing a requirement when the keyword appears
    in its filename or its opening lines - that is, when the document is
    ABOUT the requirement. A passing mention buried in the body of an
    unrelated document does not count.

    Returns a status and a short human-readable note. The note describes
    the finding - it never quotes document content.
    """
    hits = []
    for filename, text in docs:
        header = filename.lower() + " " + text[:200]
        if any(_contains(kw, header) for kw in item["keywords"]):
            hits.append((filename, text))

    if not hits:
        if item.get("conditional"):
            return MISSING, "Not found. Confirm whether applicable to this device."
        return MISSING, "No corresponding document found in the technical file."

    # Document exists. Now judge whether it is usable.
    problems = []
    for filename, text in hits:
        window = filename.lower() + " " + text
        if any(m in window for m in incomplete_markers):
            problems.append("marked as draft or unfinished")
        if any(m in window for m in wrong_regulation_markers):
            problems.append("cites EU MDR rather than UK MDR 2002")

    if problems:
        unique = sorted(set(problems))
        return INCOMPLETE, "Document present but " + "; ".join(unique) + "."

    return PRESENT, "Document present and appears complete."


def summarise(findings: list[dict]) -> dict:
    """Count findings by status, including `not_applicable`."""
    return {
        status: sum(1 for f in findings if f["status"] == status)
        for status in (PRESENT, INCOMPLETE, MISSING, NOT_APPLICABLE)
    }


def readiness(payload: dict) -> int:
    """A single 0-100 score, so the dashboard can rank nodes.

    Requirements the device agent ruled not applicable are removed from
    the denominator. Scoring a manufacturer down for not holding a
    sterilisation validation for a device it does not supply sterile
    would be the wrong answer, not a conservative one.

    A device with no applicable requirements at all scores 100 - there is
    nothing outstanding.
    """
    s = payload["summary"]
    applicable = sum(s.get(status, 0) for status in SCORED_STATUSES)
    if applicable == 0:
        return 100
    return round(100 * (s[PRESENT] + 0.5 * s[INCOMPLETE]) / applicable)


def run_gap_check(  # pylint: disable=too-many-arguments
    node_id: str,
    folder: str | Path,
    checklist: list[dict],
    incomplete_markers: list[str],
    wrong_regulation_markers: list[str],
    checklist_version: str,
    agent: DeviceAgent | None = None,
) -> dict:
    """
    The agent entry point.

    Input : a node identifier, a local folder path, the rubric the
            coordinator sent, and the device agent this node runs.
    Output: a JSON-serialisable dict of findings.

    The agent gets two say-so points per requirement. Before matching, it
    can rule the requirement not applicable to this device, in which case
    the documents are never searched for it. After matching, it can refine
    the finding. Neither may introduce document content.

    Note what is absent from the output: no filenames of missing items,
    no document text, no excerpts. Only the checklist id, a status and
    a finding note.

    `docs` goes out of scope when this function returns. Nothing derived
    from document text reaches the returned dict except the fixed status
    strings and the fixed finding notes written above.
    """
    agent = agent or DeviceAgent()
    folder = Path(folder)
    docs = _load_documents(folder)

    findings = []
    for item in checklist:
        reason = agent.resolve_applicability(item)
        if reason:
            # Ruled out before the documents are consulted at all.
            status, note = NOT_APPLICABLE, f"Not applicable: {reason}."
        else:
            status, note = _match(
                item, docs, incomplete_markers, wrong_regulation_markers
            )
            status, note = agent.extra_checks(item, status, note, docs)

        findings.append({
            "id": item["id"],
            "requirement": item["name_en"],
            "requirement_zh": item["name_zh"],
            "status": status,
            "finding": note,
        })

    return {
        "node_id": node_id,
        "agent_profile": agent.profile,
        "agent_display": agent.display,
        "checklist_version": checklist_version,
        "documents_inspected": len(docs),
        # Structurally zero. This is not a counter that happens to read 0 -
        # there is no code path in this module that puts document content
        # into the return value. If you ever add one, change this field
        # honestly or the demo is a lie.
        "documents_transmitted": 0,
        "summary": summarise(findings),
        "findings": findings,
    }
