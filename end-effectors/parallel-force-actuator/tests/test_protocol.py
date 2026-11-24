import pytest

from parallel_force_actuator import (
    corrected_counts,
    force_newton,
    home_command,
    move_command,
    parse_sample,
    rpm_for_speed,
)


def test_correction_and_newton_formula():
    assert corrected_counts(100, 2, 10) == 45
    assert force_newton(100, 2, 10, 0) == pytest.approx(45 / 573.2622826433104 * 9.81)


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
