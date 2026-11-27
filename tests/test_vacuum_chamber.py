import pytest

from qubot.end_effector.vacuum_chamber import Chamber

LOADING_POSITION = (-118.0, 0.0, 0.0)


def make_chamber():
    return Chamber(
        loading_position=LOADING_POSITION,
        close_waypoints=[(-3, 0, 0), (-3, -27, 0)],
        vacuum_on_delay_s=5,
        vacuum_off_delay_s=5,
    )


def test_close_then_evacuate_then_block_motion():
    chamber = make_chamber()
    assert chamber.close_waypoints()[0] == (-3.0, 0.0, 0.0)
    chamber.mark_closed()
    assert chamber.evacuate()[0] == "M8"
    with pytest.raises(RuntimeError):
        chamber.require_motion()
    with pytest.raises(RuntimeError):
        chamber.close_waypoints()


def test_evacuate_requires_a_closed_lid():
    with pytest.raises(RuntimeError):
        make_chamber().evacuate()


def test_home_clears_the_closed_flag_after_a_vent():
    chamber = make_chamber()
    chamber.mark_closed()
    chamber.evacuate()
    assert chamber.vent()[0] == "M9"
    chamber.mark_homed()
    chamber.require_motion()
    assert chamber.closed is False


def test_loading_position_is_outside_the_current_frame():
    with pytest.raises(RuntimeError):
        make_chamber().loading_position((-116.0, 0.0))
    assert make_chamber().loading_position((-119.0, 0.0)) == LOADING_POSITION


def test_snapshot_reports_the_last_flags():
    chamber = make_chamber()
    assert chamber.snapshot() == {"closed": False, "vented": True, "source": "last_command"}
    chamber.mark_closed()
    chamber.evacuate()
    assert chamber.snapshot()["vented"] is False


def test_configuration_is_validated():
    with pytest.raises(ValueError):
        Chamber(loading_position=(0, 0), close_waypoints=[(0, 0, 0)], vacuum_on_delay_s=1, vacuum_off_delay_s=1)
    with pytest.raises(ValueError):
        Chamber(loading_position=(0, 0, 0), close_waypoints=[], vacuum_on_delay_s=1, vacuum_off_delay_s=1)
