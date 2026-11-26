"""RepRapFirmware over serial: G-code built and sent through execute, limits enforced."""

import asyncio

import pytest

from qubot.gantry import RepRapSerialController
from qubot.geometry import Position


@pytest.fixture
def gantry(monkeypatch):
    controller = RepRapSerialController(port_name="/dev/null")
    sent = []

    def execute(command, value=None, timeout=None):
        sent.append(command)
        if command == "M114":
            return "X:10.000 Y:-20.000 Z:-5.000 A:0.000 E:0.000 Count 1 2 3"
        return "ok"

    monkeypatch.setattr(controller, "execute", execute)
    controller.sent = sent
    for axis, (low, high) in {"X": (0, 330), "Y": (-440, 0), "Z": (-140, 0), "A": (-175, 0)}.items():
        controller.set_axis_limits(axis, low, high)
    return controller


def test_terminator_is_carriage_return(gantry):
    assert gantry._build_command("G28") == "G28\r"


def test_home_all_and_one_axis(gantry):
    gantry.home()
    gantry.home(axis="z")
    assert gantry.sent[:2] == ["G28", "G28 Z"]
    with pytest.raises(ValueError):
        gantry.home(axis="Q")


def test_absolute_move_sends_gcode_and_tracks_position(gantry):
    gantry.home()
    result = gantry.move_absolute(Position(x=100, y=-200))
    assert any(cmd.startswith(("G1", "G0")) and "X100" in cmd.replace(" ", "") for cmd in gantry.sent), gantry.sent
    assert (result.x, result.y) == (100, -200)


def test_move_outside_limits_is_refused(gantry):
    gantry.home()
    before = list(gantry.sent)
    with pytest.raises(ValueError):
        gantry.move_absolute(Position(x=400))
    assert gantry.sent == before


def test_m114_position_is_parsed(gantry):
    position = asyncio.run(gantry.get_position())
    assert (position.x, position.y, position.z, position.a) == (10.0, -20.0, -5.0, 0.0)
