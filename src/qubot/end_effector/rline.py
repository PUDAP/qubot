"""Sartorius rLine model catalog from technical user manual v1.1, Table 1 and Table 3."""

from dataclasses import dataclass
from enum import Enum


class RLineModel(Enum):
    """The three rLine heads in manual v1.1."""

    UL_5_200 = "5-200"
    UL_50_1000 = "50-1000"
    UL_100_5000 = "100-5000"


@dataclass(frozen=True)
class RLineSpec:
    """Parameters that differ by rLine model."""

    model: RLineModel
    microliters_per_step: float
    home_position: int
    max_position: int
    tip_eject_position: int
    minimum_volume_ul: int
    maximum_volume_ul: int
    level_sensing: bool
    # Nominal µL/s at speed settings 1 through 6. The SI/SO command is still 1-6.
    microliters_per_second: tuple[int, int, int, int, int, int]


RLINE_SPECS: dict[RLineModel, RLineSpec] = {
    RLineModel.UL_5_200: RLineSpec(
        model=RLineModel.UL_5_200,
        microliters_per_step=0.5,
        home_position=30,
        max_position=443,
        tip_eject_position=-40,
        minimum_volume_ul=5,
        maximum_volume_ul=200,
        level_sensing=True,
        microliters_per_second=(31, 52, 80, 115, 150, 190),
    ),
    RLineModel.UL_50_1000: RLineSpec(
        model=RLineModel.UL_50_1000,
        microliters_per_step=2.5,
        home_position=30,
        max_position=443,
        tip_eject_position=-40,
        minimum_volume_ul=50,
        maximum_volume_ul=1000,
        level_sensing=True,
        microliters_per_second=(150, 265, 410, 650, 945, 1120),
    ),
    RLineModel.UL_100_5000: RLineSpec(
        model=RLineModel.UL_100_5000,
        microliters_per_step=10,
        home_position=30,
        max_position=580,
        tip_eject_position=-55,
        minimum_volume_ul=100,
        maximum_volume_ul=5000,
        level_sensing=False,
        microliters_per_second=(550, 1000, 1500, 2500, 3650, 4350),
    ),
}
