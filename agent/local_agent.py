"""
The node-side agent. This is the part that becomes your AgentApp.

It runs INSIDE the manufacturer's environment. It reads their technical
file locally and emits a structured finding per checklist item.

The single most important property of this module:
    document text is read into memory, evaluated, and discarded.
    It is never placed in the returned payload.

The return value is the only thing that crosses the network boundary.
"""

import re
from pathlib import Path

from checklist import CHECKLIST, INCOMPLETE_MARKERS, WRONG_REGULATION_MARKERS

PRESENT = "present"
INCOMPLETE = "incomplete"
MISSING = "missing"


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


def _match(item: dict, docs: list[tuple[str, str]]) -> tuple[str, str]:
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
        if any(m in window for m in INCOMPLETE_MARKERS):
            problems.append("marked as draft or unfinished")
        if any(m in window for m in WRONG_REGULATION_MARKERS):
            problems.append("cites EU MDR rather than UK MDR 2002")

    if problems:
        unique = sorted(set(problems))
        return INCOMPLETE, "Document present but " + "; ".join(unique) + "."

    return PRESENT, "Document present and appears complete."


def run_gap_check(node_id: str, folder: str | Path) -> dict:
    """
    The agent entry point.

    Input : a node identifier and a local folder path.
    Output: a JSON-serialisable dict of findings.

    Note what is absent from the output: no filenames of missing items,
    no document text, no excerpts. Only the checklist id, a status and
    a finding note.
    """
    folder = Path(folder)
    docs = _load_documents(folder)

    findings = []
    for item in CHECKLIST:
        status, note = _match(item, docs)
        findings.append({
            "id": item["id"],
            "requirement": item["name_en"],
            "requirement_zh": item["name_zh"],
            "status": status,
            "finding": note,
        })

    counts = {
        PRESENT: sum(1 for f in findings if f["status"] == PRESENT),
        INCOMPLETE: sum(1 for f in findings if f["status"] == INCOMPLETE),
        MISSING: sum(1 for f in findings if f["status"] == MISSING),
    }

    return {
        "node_id": node_id,
        "checklist_version": "GB-CLASS-IIa-v1",
        "documents_inspected": len(docs),
        "documents_transmitted": 0,
        "summary": counts,
        "findings": findings,
    }


if __name__ == "__main__":
    import json
    import sys

    node = sys.argv[1] if len(sys.argv) > 1 else "manufacturer_a"
    base = Path(__file__).parent.parent / "nodes" / node
    print(json.dumps(run_gap_check(node, base), indent=2, ensure_ascii=False))
