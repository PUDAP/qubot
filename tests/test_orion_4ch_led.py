import pytest

from qubot.end_effector.orion_4ch_led import power_line


def test_power_line_matches_the_board_format():
    assert power_line([65, 100, 105, 105]) == "65;100;105;105\n"
    assert power_line([0, 0, 0, 0]) == "0;0;0;0\n"


def test_power_line_rejects_a_bad_frame():
    with pytest.raises(ValueError):
        power_line([0, 0, 0])
    with pytest.raises(ValueError):
        power_line([0, 0, 0, -1])
