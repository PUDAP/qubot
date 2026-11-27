"""One Sartorius rLine body, model 5-200 uL, 0.5 uL/step.

The edge supplies the serial port; callers cannot override the physical model.
"""

from .rline import RLINE_SPECS, RLineModel
from .satorius import SatoriusController

MODEL = RLineModel.UL_5_200
COMMUNICATION = "serial"
MICROLITERS_PER_STEP = RLINE_SPECS[MODEL].microliters_per_step


def connect(port_name: str) -> SatoriusController:
    """Open this physical 5-200 uL body."""
    return SatoriusController(port_name=port_name, model=MODEL)


__all__ = [
    "COMMUNICATION",
    "MICROLITERS_PER_STEP",
    "MODEL",
    "RLineModel",
    "SatoriusController",
    "connect",
]
