"""
The manufacturer-side ClientApp.

This process runs on the manufacturer's own machine, started by their own
`flower-supernode`. It is the only component in the system that is allowed
to touch the technical file, and the SuperNode operator decides where that
is by passing `--node-config 'data-dir="..."'` at startup. Nothing in the
coordinator's app can change that path.
"""

import json
from pathlib import Path

from flwr.app import ConfigRecord, Context, Error, Message, RecordDict
from flwr.clientapp import ClientApp

from gapcheck_app.gap_check import run_gap_check

# flwr.common.constant.ErrorCode.CLIENT_APP_RAISED_EXCEPTION. Inlined to keep
# this module on the public `flwr.app` API surface only.
_ERROR_APP_FAILED = 2

app = ClientApp()


@app.query("gap_check")
def gap_check(msg: Message, context: Context) -> Message:
    """Assess the local technical file and return findings only."""
    node_config = context.node_config

    # --- locate the local technical file -------------------------------
    # Configured by the node operator, never by the coordinator. Refuse
    # loudly rather than silently reporting an empty folder as 12 gaps.
    raw_dir = node_config.get("data-dir")
    if not raw_dir:
        return Message(
            Error(
                _ERROR_APP_FAILED,
                "This SuperNode has no 'data-dir' in its --node-config, so "
                "there is no technical file to assess.",
            ),
            reply_to=msg,
        )

    folder = Path(str(raw_dir)).expanduser()
    if not folder.is_dir():
        return Message(
            Error(_ERROR_APP_FAILED, f"data-dir is not a directory: {folder}"),
            reply_to=msg,
        )

    # Identity is the node's own to declare. The coordinator learns who
    # answered from the reply, it does not hold a roster of who exists.
    node_id = str(node_config.get("node-name") or folder.name)
    display_name = str(node_config.get("display-name") or "")

    # --- unpack the rubric the coordinator sent ------------------------
    # We evaluate against the checklist we were handed, not a local copy.
    rubric = json.loads(str(msg.content["checklist"]["json"]))

    payload = run_gap_check(
        node_id=node_id,
        folder=folder,
        checklist=rubric["checklist"],
        incomplete_markers=rubric["incomplete_markers"],
        wrong_regulation_markers=rubric["wrong_regulation_markers"],
        checklist_version=rubric["checklist_version"],
    )
    if display_name:
        payload["display_name"] = display_name

    # --- THE RED LINE --------------------------------------------------
    # `payload` is everything that leaves this machine. It contains, per
    # checklist item: an id, a requirement name, a status, and a finding
    # note drawn from a fixed set of sentences. It does not contain
    # document text, excerpts, filenames, or paths - not even for the
    # documents that are missing.
    #
    # Document text was read inside run_gap_check() and went out of scope
    # when it returned. Do not add anything to `payload` here.
    content = RecordDict(
        {"findings": ConfigRecord({"json": json.dumps(payload, ensure_ascii=False)})}
    )
    return Message(content, reply_to=msg)
