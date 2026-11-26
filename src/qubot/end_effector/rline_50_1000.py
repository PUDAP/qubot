"""One Sartorius rLine body, model 50-1000 uL, 2.5 uL/step. Axis Z, serial `SATORIUS_PORT`. No host address is stored here.
"""

from .rline import RLINE_SPECS, RLineModel
from .satorius import SatoriusController

MODEL = RLineModel.UL_50_1000
AXIS = "Z"
PORT_ENV = "SATORIUS_PORT"
COMMUNICATION = "serial"
MICROLITERS_PER_STEP = RLINE_SPECS[MODEL].microliters_per_step


def connect(port_name: str) -> SatoriusController:
    """Open this physical 50-1000 uL body. The model is not a caller choice."""
    return SatoriusController(port_name=port_name, model=MODEL)


__all__ = [
    "AXIS",
    "COMMUNICATION",
    "MICROLITERS_PER_STEP",
    "MODEL",
    "PORT_ENV",
    "RLineModel",
    "SatoriusController",
    "connect",
]
