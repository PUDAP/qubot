from qubot.end_effector.rotating_vacuum_gripper import pulse_for_yaw, require_rotation_height, valve_command
import pytest


def test_calibrated_yaw_pulses():
    assert pulse_for_yaw(0) == 14
    assert pulse_for_yaw(-90) == 124
    assert pulse_for_yaw(-180) == 244


def test_intermediate_pulse_stays_on_the_calibrated_segment():
    assert pulse_for_yaw(-45) == 69
    assert pulse_for_yaw(-135) == 184


def test_yaw_outside_range_is_rejected():
    with pytest.raises(ValueError):
        pulse_for_yaw(1)
    with pytest.raises(ValueError):
        pulse_for_yaw(-181)


def test_valve_commands_and_delays():
    assert valve_command(True) == ("M8", 3.0)
    assert valve_command(False) == ("M9", 3.0)


def test_rotation_requires_the_safe_height():
    require_rotation_height(-5)
    with pytest.raises(RuntimeError):
        require_rotation_height(-5.1)
