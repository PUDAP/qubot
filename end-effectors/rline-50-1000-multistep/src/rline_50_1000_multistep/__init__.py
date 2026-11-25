from .pace import RESPONSE_TIME_S, STEP_RESOLUTION
from .rline import RLINE_SPECS, RLineModel, SELECTED_MODEL
from .satorius import SatoriusController

MODEL = SELECTED_MODEL
AXIS = "Z"
PORT_ENV = "SATORIUS_PORT"
COMMUNICATION = "serial"
MICROLITERS_PER_STEP = RLINE_SPECS[MODEL].microliters_per_step
MINIMUM_VOLUME_UL = RLINE_SPECS[MODEL].minimum_volume_ul
MAXIMUM_VOLUME_UL = RLINE_SPECS[MODEL].maximum_volume_ul


def connect(
    port_name: str,
    *,
    step_resolution: int = STEP_RESOLUTION,
    response_time_s: float = RESPONSE_TIME_S,
) -> SatoriusController:
    """Open this physical 50-1000 uL body. The model is not a caller choice.

    ``step_resolution`` and ``response_time_s`` are the calibrated multistep
    limits. They default to 10 steps and 1.03 seconds.
    """
    return SatoriusController(
        port_name=port_name,
        model=MODEL,
        step_resolution=step_resolution,
        response_time_s=response_time_s,
    )


__all__ = [
    "AXIS",
    "COMMUNICATION",
    "MAXIMUM_VOLUME_UL",
    "MICROLITERS_PER_STEP",
    "MINIMUM_VOLUME_UL",
    "MODEL",
    "PORT_ENV",
    "RESPONSE_TIME_S",
    "RLineModel",
    "STEP_RESOLUTION",
    "SatoriusController",
    "connect",
]
