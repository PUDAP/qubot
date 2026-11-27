import pytest

from qubot.end_effector.parallel_force_actuator import (
    corrected_counts,
    Finger,
    ParallelFingers,
    force_newton,
    home_command,
    move_command,
    parse_sample,
    rpm_for_speed,
)


def test_correction_and_newton_formula():
    assert corrected_counts(100, 2, 10) == 45
    assert force_newton(100, 2, 10, 0, 573.2622826433104) == pytest.approx(45 / 573.2622826433104 * 9.81)


def test_stream_line_and_commands():
    sample = parse_sample("-26.5,106, -26.5,0,1200\r\n")
    assert sample["displacement_mm"] == pytest.approx(-26.5)
    assert sample["end_stop"] is False
    assert sample["raw"] == 1200
    assert home_command() == "H 0\r\n"
    assert rpm_for_speed(1 / 60) == 106
    assert move_command(-26.5, 106) == "G -26.5 106\r\n"


def test_limits_reject_a_target_past_minus_30():
    with pytest.raises(ValueError):
        move_command(-30.1, 100)


def test_limits_can_be_configured():
    assert move_command(-40.5, 100, (-50.0, 0.0)) == "G -40.5 100\r\n"


def test_fingers_take_one_correction_per_port():
    fingers = ParallelFingers(["a", "b"], corrections=[(1.0, 0.0), (2.0, 5.0)], calibration_factor=500.0)
    assert fingers.finger(1).slope == 2.0
    assert fingers.finger(1).intercept == 5.0
    with pytest.raises(ValueError):
        fingers.finger(2)
    with pytest.raises(ValueError):
        ParallelFingers(["a", "b"], corrections=[(1.0, 0.0)], calibration_factor=500.0)
    with pytest.raises(ValueError):
        Finger("a", 0, slope=0, intercept=0, calibration_factor=1)


def test_stopping_force_holds_and_none_does_not():
    finger = Finger("unused", 0, slope=1, intercept=0, calibration_factor=1)
    finger._latest = {"displacement_mm": -10.0, "force_n": 8000}
    assert finger._wait_displacement(-30, 0.05, stopping_force=7500) == -10.0
    assert finger._stopped_on_force is True
    with pytest.raises(RuntimeError):
        finger._wait_displacement(-30, 0.05, stopping_force=None)


def test_snapshot_keeps_a_silent_channel():
    fingers = ParallelFingers(["a", "b"], corrections=[(1.0, 0.0), (1.0, 0.0)], calibration_factor=1)
    fingers.finger(1)._latest = {"channel": 1, "force_n": 1.5}
    snapshot = fingers.snapshot()
    assert snapshot["channels"]["0"] == {"channel": 0}
    assert snapshot["channels"]["1"]["force_n"] == 1.5
    snapshot["channels"]["1"]["force_n"] = 0
    assert fingers.finger(1).latest()["force_n"] == 1.5
