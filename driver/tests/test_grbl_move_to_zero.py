import pytest

from qubot_drivers.move.grblHAL import AxisLimits, GrblHALController
from qubot_drivers.position import Position


def test_move_absolute_to_zero_moves_z_from_nonzero_position():
    controller = GrblHALController(port_name="/dev/does-not-open-in-this-test")
    controller._axis_limits = {
        "X": AxisLimits(0.0, 161.7),
        "Y": AxisLimits(-444.5, 0.0),
        "Z": AxisLimits(-175.0, 0.0),
    }
    controller._current_position = Position(x=16.94, y=-288.32, z=-82.5)
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"
    controller._wait_for_move = lambda: None

    result = controller.move_absolute(
        Position(x=16.94, y=-288.32, z=0.0)
    )

    assert commands == ["G90", "G1 Z0.0 F1000"]
    assert result.x == pytest.approx(16.94)
    assert result.y == pytest.approx(-288.32)
    assert result.z == pytest.approx(0.0)
