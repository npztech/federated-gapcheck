"""
The UKRP-side ServerApp.

This is the federated replacement for agent/coordinator.py::_dispatch().
The signature of the exchange is unchanged - a node in, a findings dict
out - but the call now crosses a network to a machine the coordinator
does not control and cannot read.

The coordinator never sees a nodes/ folder. Its only input is the findings
payload each node chooses to return, including which device agent that
node chose to run.
"""

import json
from pathlib import Path

from flwr.app import ConfigRecord, Context, Message, RecordDict
from flwr.serverapp import Grid, ServerApp

from gapcheck_app.checklist import (
    CHECKLIST,
    INCOMPLETE_MARKERS,
    WRONG_REGULATION_MARKERS,
)
from gapcheck_app.dashboard import build_dashboard
from gapcheck_app.gap_check import (
    INCOMPLETE,
    MISSING,
    NOT_APPLICABLE,
    PRESENT,
    readiness,
)

MESSAGE_TYPE = "query.gap_check"

app = ServerApp()


def _rubric(checklist_version: str) -> str:
    """Serialise the checklist for transmission.

    This is the only payload that travels outward from the coordinator. It
    is a generic requirements list - it contains no client data, and it is
    identical for every node. Which of these requirements actually apply
    is decided on the node, by the node's own device agent.
    """
    return json.dumps(
        {
            "checklist_version": checklist_version,
            "checklist": CHECKLIST,
            "incomplete_markers": INCOMPLETE_MARKERS,
            "wrong_regulation_markers": WRONG_REGULATION_MARKERS,
        },
        ensure_ascii=False,
    )


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Distribute the checklist, collect findings, report."""
    checklist_version = str(context.run_config["checklist-version"])
    timeout = float(context.run_config["round-timeout"])
    output_dir = str(context.run_config["output-dir"]).strip()

    node_ids = list(grid.get_node_ids())
    if not node_ids:
        raise RuntimeError(
            "No SuperNodes are connected to this SuperLink, so there is "
            "nothing to assess. Start at least one `flower-supernode` with "
            "--node-config 'data-dir=\"...\"' and run again."
        )

    print(f"\nDistributing {checklist_version} to {len(node_ids)} node(s)...")

    content = RecordDict(
        {"checklist": ConfigRecord({"json": _rubric(checklist_version)})}
    )
    messages = [
        Message(
            content,
            dst_node_id=node_id,
            message_type=MESSAGE_TYPE,
            group_id="1",
        )
        for node_id in node_ids
    ]

    replies = list(grid.send_and_receive(messages, timeout=timeout))

    results: list[dict] = []
    failures: list[tuple[int, str]] = []
    for reply in replies:
        # One unreachable node must not cost us the other two.
        if reply.has_error():
            failures.append(
                (reply.metadata.src_node_id, reply.error.reason or "unknown error")
            )
            continue
        payload = json.loads(str(reply.content["findings"]["json"]))
        payload.setdefault("display_name", "")
        payload.setdefault("agent_profile", "generic")
        results.append(payload)

    answered = len(results) + len(failures)
    if answered < len(node_ids):
        failures.append((0, f"{len(node_ids) - answered} node(s) did not reply in time"))

    results.sort(key=lambda r: r["node_id"])

    _report(results, failures)

    if output_dir:
        out = Path(output_dir).expanduser()
        out.mkdir(parents=True, exist_ok=True)

        findings_path = out / "findings.json"
        findings_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        dashboard_path = out / "dashboard.html"
        dashboard_path.write_text(
            build_dashboard(results, CHECKLIST), encoding="utf-8"
        )

        print(f"\nWritten to {findings_path}")
        print(f"Written to {dashboard_path}")


def _report(results: list[dict], failures: list[tuple[int, str]]) -> None:
    """Print the summary table."""
    print("Federated gap check complete.\n")
    for r in results:
        s = r["summary"]
        print(f'  {r["node_id"]:<16} '
              f'{r["agent_profile"]:<11} '
              f'present {s[PRESENT]:>2}  '
              f'incomplete {s[INCOMPLETE]:>2}  '
              f'missing {s[MISSING]:>2}  '
              f'n/a {s.get(NOT_APPLICABLE, 0):>2}   '
              f'readiness {readiness(r)}%')

    for node_id, reason in failures:
        label = f"node {node_id}" if node_id else "timeout"
        print(f'  {label:<16} NO RESULT - {reason}')

    print(f"\n  documents inspected  : {sum(r['documents_inspected'] for r in results)}")
    print(f"  documents transferred: {sum(r['documents_transmitted'] for r in results)}")
