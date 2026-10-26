"""rLine model catalog matches manual v1.1 Table 1 and Table 3."""

import pytest

from qubot_drivers.rline import RLINE_SPECS, RLineModel
from qubot_drivers.satorius import SatoriusController


def test_catalog_matches_manual_table_1_and_table_3():
    small = RLINE_SPECS[RLineModel.UL_5_200]
    medium = RLINE_SPECS[RLineModel.UL_50_1000]
    large = RLINE_SPECS[RLineModel.UL_100_5000]

    assert small.microliters_per_step == 0.5
    assert medium.microliters_per_step == 2.5
    assert large.microliters_per_step == 10
    assert (small.home_position, medium.home_position, large.home_position) == (30, 30, 30)
    assert (small.max_position, medium.max_position, large.max_position) == (443, 443, 580)
    assert (small.tip_eject_position, medium.tip_eject_position, large.tip_eject_position) == (
        -40,
        -40,
        -55,
    )
    assert small.level_sensing and medium.level_sensing and not large.level_sensing
    assert small.microliters_per_second == (31, 52, 80, 115, 150, 190)
    assert medium.microliters_per_second == (150, 265, 410, 650, 945, 1120)
    assert large.microliters_per_second == (550, 1000, 1500, 2500, 3650, 4350)


def test_omitting_model_raises():
    with pytest.raises(TypeError):
        SatoriusController(port_name="fake")


def test_volume_past_max_position_is_rejected_before_write(monkeypatch):
    controller = SatoriusController(model=RLineModel.UL_5_200)

    def fail_execute(*args, **kwargs):
        raise AssertionError("serial write should not run")

    monkeypatch.setattr(controller, "execute", fail_execute)

    with pytest.raises(ValueError, match="max position 443"):
        controller.aspirate(250)
