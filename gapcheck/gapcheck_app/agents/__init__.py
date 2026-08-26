"""
Device agent registry.

A SuperNode selects its agent with `--node-config 'agent-profile="..."'`.
The profile names are the keys of PROFILES below.

Two behaviours worth being deliberate about:

  * **No profile set** falls back to the generic agent, which applies the
    full checklist. That is the behaviour of the build before agents
    existed, so a node that has not been migrated still works.

  * **An unrecognised profile is an error**, not a fallback. A typo in
    `agent-profile` would otherwise silently produce a different set of
    numbers with nothing to indicate it, which is worse than refusing to
    start.
"""

from __future__ import annotations

from .base import DeviceAgent
from .class1_device_agent import Class1DeviceAgent
from .electronic_device_agent import ElectronicDeviceAgent
from .sterile_device_agent import SterileDeviceAgent

PROFILES: dict[str, type[DeviceAgent]] = {
    SterileDeviceAgent.profile: SterileDeviceAgent,
    ElectronicDeviceAgent.profile: ElectronicDeviceAgent,
    Class1DeviceAgent.profile: Class1DeviceAgent,
}


class UnknownAgentProfileError(ValueError):
    """Raised when a SuperNode declares an agent profile that is not known."""


def load_agent(profile: str | None) -> DeviceAgent:
    """Return the agent for `profile`, or the generic agent if unset.

    Parameters
    ----------
    profile : str | None
        The value of `agent-profile` from the SuperNode's node config.
        None or empty selects the generic agent.

    Raises
    ------
    UnknownAgentProfileError
        If `profile` is set but does not name a registered agent.
    """
    if profile is None or not str(profile).strip():
        return DeviceAgent()

    key = str(profile).strip().lower()
    agent_cls = PROFILES.get(key)
    if agent_cls is None:
        known = ", ".join(sorted(PROFILES))
        raise UnknownAgentProfileError(
            f"Unknown agent-profile {profile!r}. Known profiles: {known}. "
            "Omit agent-profile entirely to use the generic agent."
        )
    return agent_cls()


__all__ = [
    "Class1DeviceAgent",
    "DeviceAgent",
    "ElectronicDeviceAgent",
    "PROFILES",
    "SterileDeviceAgent",
    "UnknownAgentProfileError",
    "load_agent",
]
