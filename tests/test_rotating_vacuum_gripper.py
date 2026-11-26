import pytest

from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper


def gripper(**overrides):
    values = dict(
        axis="C",
        yaw_pulses=[(0, 14), (-90, 124), (-180, 244)],
        rotation_min_z_mm=-5,
        vacuum_on_delay_s=3,
        vacuum_off_delay_s=3,
    )
    values.update(overrides)
    return RotatingVacuumGripper(**values)


def test_calibrated_yaw_pulses():
    g = gripper()
    assert g.pulse_for_yaw(0) == 14
    assert g.pulse_for_yaw(-90) == 124
    assert g.pulse_for_yaw(-180) == 244
    assert g.servo_command(-90) == "M3 S124"


def test_intermediate_pulse_stays_on_the_calibrated_segment():
    g = gripper()
    assert g.pulse_for_yaw(-45) == 69
    assert g.pulse_for_yaw(-135) == 184


def test_points_are_sorted_and_set_the_yaw_span():
    g = gripper(yaw_pulses=[(-180, 244), (0, 14), (-90, 124)])
    assert (g.yaw_min_deg, g.yaw_max_deg) == (-180, 0)
    assert g.pulse_for_yaw(-45) == 69


def test_yaw_outside_range_is_rejected():
    g = gripper()
    with pytest.raises(ValueError):
        g.pulse_for_yaw(1)
    with pytest.raises(ValueError):
        g.pulse_for_yaw(-181)


def test_bad_calibration_is_rejected():
    with pytest.raises(ValueError):
        gripper(yaw_pulses=[(0, 14)])
    with pytest.raises(ValueError):
        gripper(yaw_pulses=[(0, 14), (0, 20)])


def test_valve_commands_and_delays():
    g = gripper()
    assert g.valve_command(True) == ("M8", 3.0)
    assert g.valve_command(False) == ("M9", 3.0)


def test_rotation_requires_the_safe_height():
    g = gripper()
    g.require_rotation_height(-5)
    with pytest.raises(RuntimeError):
        g.require_rotation_height(-5.1)
