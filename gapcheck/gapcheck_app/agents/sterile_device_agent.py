"""
Agent for sterile, body-contacting devices.

Example: infusion sets. Supplied sterile, fluid path contacts the patient,
and Class IIa or above — so the three conditional requirements all apply:

    R05 biological evaluation   applies, the device contacts the body
    R06 sterilisation validation applies, the device is supplied sterile
    R09 Approved Body certificate applies, Class IIa needs one

Nothing is ruled out, so this agent's findings are identical to the
generic agent's. It exists to make the claim explicit: the full checklist
is the right checklist for this device, and that was a decision, not a
default.
"""

from .base import DeviceAgent


class SterileDeviceAgent(DeviceAgent):
    """Sterile body-contacting device. Full checklist applies."""

    profile = "sterile"
    display = "Sterile body-contacting device"
    description = (
        "Supplied sterile and body-contacting, Class IIa or above. Every "
        "requirement including R05, R06 and R09 applies."
    )
