"""Sartorius rLine 50-1000 µL body, 2.5 µL/step. Manual v1.1 Table 1: home 30, max 443, tip eject −40. The six preset speeds are 150, 265, 410, 650, 945, and 1120 µL/s. This is not the 5-200 µL body (0.5 µL/step) and not the 100-5000 µL body (10 µL/step).

`aspirate` and `dispense` take `speed_ul_s`. A preset speed is one `RI` or `RO`. Any other positive speed uses a faster preset, split into several moves. The pause after each move makes the transfer take `volume / speed` seconds. `step_resolution` and `response_time_s` are per-pipette calibrations the edge passes in: the smallest step that keeps the volume error tolerable, and the shortest command round-trip the plan is allowed to assume. A speed this calibration cannot hit raises. Nothing faster than 1120 µL/s is possible.

A dispense of the whole tracked volume paces those outward steps and then sends `RB`.

The edge passes the serial port. `rline-50-1000` is unchanged.
"""

from .rline import RLINE_SPECS, RLineModel
from .satorius_multistep import SatoriusController

# Locked to the 50-1000 uL body. Table 1 of rLine manual v1.1:
# 2.5 uL/step, not 0.5 (5-200) or 10 (100-5000).
SELECTED_MODEL = RLineModel.UL_50_1000
MODEL = SELECTED_MODEL
COMMUNICATION = "serial"
MICROLITERS_PER_STEP = RLINE_SPECS[MODEL].microliters_per_step
MINIMUM_VOLUME_UL = RLINE_SPECS[MODEL].minimum_volume_ul
MAXIMUM_VOLUME_UL = RLINE_SPECS[MODEL].maximum_volume_ul


def connect(
    port_name: str,
    *,
    step_resolution: int,
    response_time_s: float,
) -> SatoriusController:
    """Open this physical 50-1000 uL body. The model is not a caller choice.

    ``step_resolution`` and ``response_time_s`` are this pipette's calibrated
    multistep limits, from the edge contract.
    """
    return SatoriusController(
        port_name=port_name,
        model=MODEL,
        step_resolution=step_resolution,
        response_time_s=response_time_s,
    )


__all__ = [
    "COMMUNICATION",
    "MAXIMUM_VOLUME_UL",
    "MICROLITERS_PER_STEP",
    "MINIMUM_VOLUME_UL",
    "MODEL",
    "RLineModel",
    "SELECTED_MODEL",
    "SatoriusController",
    "connect",
]
