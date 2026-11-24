import pytest

from vacuum_chamber import LOADING_POSITION, Chamber


def test_close_then_evacuate_then_block_motion():
    chamber = Chamber()
    assert chamber.close_waypoints()[0] == (-3.0, 0.0, 0.0)
    chamber.mark_closed()
    assert chamber.evacuate()[0] == "M8"
    with pytest.raises(RuntimeError):
        chamber.require_motion()
    with pytest.raises(RuntimeError):
        chamber.close_waypoints()


def test_evacuate_requires_a_closed_lid():
    with pytest.raises(RuntimeError):
        Chamber().evacuate()


def test_home_clears_the_closed_flag_after_a_vent():
    chamber = Chamber()
    chamber.mark_closed()
    chamber.evacuate()
    assert chamber.vent()[0] == "M9"
    chamber.mark_homed()
    chamber.require_motion()
    assert chamber.closed is False


def test_loading_position_is_outside_the_current_frame():
    with pytest.raises(RuntimeError):
        Chamber().loading_position((-116.0, 0.0))
    assert Chamber().loading_position((-119.0, 0.0)) == LOADING_POSITION
