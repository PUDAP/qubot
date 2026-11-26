"""One Sartorius rLine body, model 50-1000 uL, 2.5 uL/step. The edge passes the serial port.
"""

from .rline import RLINE_SPECS, RLineModel
from .satorius import SatoriusController

MODEL = RLineModel.UL_50_1000
COMMUNICATION = "serial"
MICROLITERS_PER_STEP = RLINE_SPECS[MODEL].microliters_per_step


def connect(port_name: str) -> SatoriusController:
    """Open this physical 50-1000 uL body. The model is not a caller choice."""
    return SatoriusController(port_name=port_name, model=MODEL)


__all__ = [
    "COMMUNICATION",
    "MICROLITERS_PER_STEP",
    "MODEL",
    "RLineModel",
    "SatoriusController",
    "connect",
]
