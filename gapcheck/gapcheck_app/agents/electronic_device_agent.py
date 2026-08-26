"""
Agent for non-invasive electronic devices.

Example: clinical thermometers. An electronic instrument that does not
enter the body and is not supplied sterile, so two of the conditional
requirements do not apply to it:

    R05 biological evaluation    not applicable, non-invasive
    R06 sterilisation validation not applicable, supplied non-sterile

R09 is left applicable. Whether an Approved Body is required depends on
the device's classification, which this agent does not attempt to infer -
so it stays on the checklist rather than being quietly dropped.
"""

from .base import DeviceAgent

_NOT_APPLICABLE = "non-invasive electronic device, supplied non-sterile"


class ElectronicDeviceAgent(DeviceAgent):
    """Non-invasive electronic device. R05 and R06 do not apply."""

    profile = "electronic"
    display = "Non-invasive electronic device"
    description = (
        "Electronic instrument that does not enter the body and is not "
        "supplied sterile. R05 and R06 do not apply."
    )

    def resolve_applicability(self, item: dict) -> str | None:
        """Rule out the two requirements this device cannot trigger."""
        if item["id"] in ("R05", "R06"):
            return _NOT_APPLICABLE
        return None
