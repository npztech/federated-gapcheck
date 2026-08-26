"""
Agent for Class I non-sterile devices.

Example: orthopaedic supports. The lowest risk class, self-certified,
supplied non-sterile:

    R06 sterilisation validation  not applicable, supplied non-sterile
    R09 Approved Body certificate not applicable, Class I non-sterile is
                                  self-certified under UK MDR 2002

R05 is left applicable. A support is body-contacting, so a biological
evaluation can still be required depending on materials and contact
duration - this agent does not rule it out.
"""

from .base import DeviceAgent

_NON_STERILE = "supplied non-sterile"
_SELF_CERTIFIED = (
    "Class I non-sterile: no Approved Body conformity assessment required"
)


class Class1DeviceAgent(DeviceAgent):
    """Class I non-sterile device. R06 and R09 do not apply."""

    profile = "class1"
    display = "Class I non-sterile device"
    description = (
        "Lowest risk class, self-certified, supplied non-sterile. R06 and "
        "R09 do not apply."
    )

    def resolve_applicability(self, item: dict) -> str | None:
        """Rule out sterilisation and Approved Body requirements."""
        if item["id"] == "R06":
            return _NON_STERILE
        if item["id"] == "R09":
            return _SELF_CERTIFIED
        return None
