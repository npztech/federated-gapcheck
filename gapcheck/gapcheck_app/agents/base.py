"""
Base device agent.

An agent decides two things about a requirement, on the node, before and
after the shared matcher looks at the documents:

    resolve_applicability(item) -> str | None
        Return None if the requirement applies to this device, or a short
        reason if it does not. A requirement ruled not applicable is never
        matched against the technical file at all.

    extra_checks(item, status, note, docs) -> (status, note)
        Optionally refine a finding after the shared matcher has run.
        The default returns it unchanged.

This class is also the generic agent: it treats every requirement as
applicable and refines nothing, which is exactly the behaviour of the
build that had no agent profiles. A SuperNode that sets no `agent-profile`
gets this, so an un-migrated node keeps working.

Nothing here reads or returns document text. `docs` is passed to
extra_checks so a profile can inspect the file it already has in memory,
under the same rule as the rest of the node code: findings out, never
content.
"""

from __future__ import annotations


class DeviceAgent:
    """Generic agent. Every requirement applies; no extra checks."""

    profile = "generic"
    display = "Generic device"
    description = (
        "Applies the full checklist. Used when a SuperNode declares no "
        "agent-profile."
    )

    def resolve_applicability(self, item: dict) -> str | None:
        """Return None if `item` applies to this device, else a reason."""
        return None

    # pylint: disable-next=unused-argument
    def extra_checks(
        self,
        item: dict,
        status: str,
        note: str,
        docs: list[tuple[str, str]],
    ) -> tuple[str, str]:
        """Refine one finding. The default changes nothing."""
        return status, note

    def __repr__(self) -> str:
        return f"{type(self).__name__}(profile={self.profile!r})"
