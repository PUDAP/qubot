import math

import pytest

from qubot_drivers import Position
from qubot_drivers.move.grblHAL import AxisLimits, GrblHALController


def make_controller() -> GrblHALController:
    controller = GrblHALController(port_name="/dev/not-opened-in-unit-tests")
    controller._axis_limits = {
        "X": AxisLimits(-175.0, 0.0),
        "Y": AxisLimits(-190.0, 0.0),
        "Z": AxisLimits(-75.0, 0.0),
    }
    controller._current_position = Position(x=-100.0, y=-100.0, z=-10.0)
    return controller


def test_xy_move_rejects_safe_height_outside_limits_before_transmission():
    controller = make_controller()
    controller._axis_limits["Z"] = AxisLimits(-75.0, -6.0)
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"

    with pytest.raises(ValueError, match="outside axis limits"):
        controller.move_absolute(Position(x=-90.0, y=-100.0, z=-10.0))

    assert commands == []


@pytest.mark.parametrize("response", ["error:9", "ALARM:2", "", None])
def test_controller_failure_stops_move_without_updating_position(response):
    controller = make_controller()
    original = controller.get_internal_position()
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or response

    with pytest.raises(RuntimeError, match="G90.*failed"):
        controller.move_absolute(Position(x=-90.0, y=-100.0, z=-10.0))

    assert commands == ["G90"]
    assert controller.get_internal_position() == original


def test_motion_command_error_does_not_advance_internal_position():
    controller = make_controller()
    original = controller.get_internal_position()
    commands = []

    def execute(command, **_kwargs):
        commands.append(command)
        return "error:9" if command.startswith("G1") else "ok"

    controller.execute = execute

    with pytest.raises(RuntimeError, match="G1 Z-5.*error:9"):
        controller.move_absolute(Position(x=-90.0, y=-100.0, z=-10.0))

    assert commands == ["G90", "G1 Z-5 F1000"]
    assert controller.get_internal_position() == original


def test_get_info_uses_native_grbl_build_info_query():
    controller = make_controller()
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "[VER:1.1h:]\nok"

    assert controller.get_info() == "[VER:1.1h:]\nok"
    assert commands == ["$I"]


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (math.nan, 0.0),
        (-175.0, math.nan),
        (-math.inf, 0.0),
        (-175.0, math.inf),
    ],
)
def test_axis_limit_configuration_rejects_non_finite_values(minimum, maximum):
    controller = make_controller()
    original = controller.get_axis_limits("X")

    with pytest.raises(ValueError, match="finite"):
        controller.set_axis_limits("X", minimum, maximum)

    assert controller.get_axis_limits("X") == original


def test_axis_limit_boundaries_are_inclusive():
    limits = AxisLimits(-175.0, 0.0)

    limits.validate(-175.0)
    limits.validate(0.0)


@pytest.mark.parametrize("target", [-175.001, 0.001, math.nan, math.inf, -math.inf])
def test_absolute_out_of_range_target_is_rejected_before_transmission(target):
    controller = make_controller()
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"

    with pytest.raises(ValueError):
        controller.move_absolute(Position(x=target))

    assert commands == []


def test_relative_move_rejects_out_of_range_result_before_transmission():
    controller = make_controller()
    controller._current_position = Position(x=-174.0, y=-100.0, z=-10.0)
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"

    with pytest.raises(ValueError, match="outside axis limits"):
        controller.move_relative(Position(x=-2.0))

    assert commands == []


def test_read_status_requires_state_and_mpos():
    controller = make_controller()
    controller.execute = lambda command, **_kwargs: (
        "<Idle|MPos:1.000,-2.500,-3.000|FS:0,0>\r\nok"
    )

    report = controller.read_status()

    assert report.state == "Idle"
    assert report.position.x == 1.0
    assert report.position.y == -2.5
    assert report.position.z == -3.0


def test_read_status_rejects_an_incomplete_report():
    controller = make_controller()
    controller.execute = lambda command, **_kwargs: "ok"

    with pytest.raises(RuntimeError, match="incomplete"):
        controller.read_status()


def test_default_home_does_not_query_status():
    controller = make_controller()
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"

    controller.home()

    assert commands == ["$H"]


def test_verified_home_requires_idle_at_zero_before_clearing_position():
    controller = make_controller()
    original = controller.get_internal_position()
    commands = []

    def execute(command, **_kwargs):
        commands.append(command)
        if command == "?":
            return "<Alarm|MPos:1.000,0.000,0.000|FS:0,0>"
        return "ok"

    controller.execute = execute

    with pytest.raises(RuntimeError, match="Idle"):
        controller.home(verify_origin=True)

    assert commands == ["$H", "?"]
    assert controller.get_internal_position() == original


def test_verified_home_accepts_idle_origin():
    controller = make_controller()

    def execute(command, **_kwargs):
        if command == "?":
            return "<Idle|MPos:0.000,0.000,0.000|FS:0,0>\r\nok"
        return "ok"

    controller.execute = execute
    controller.home(verify_origin=True)

    assert controller.get_internal_position() == Position(x=0.0, y=0.0, z=0.0)


def test_direct_move_skips_safe_z_lift():
    controller = make_controller()
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"
    controller._wait_for_move = lambda timeout=None: None

    controller.move_absolute(
        Position(x=-90.0, y=-80.0, z=-20.0),
        feed=100,
        apply_safe_z=False,
    )

    assert commands == ["G90", "G1 X-90.0 Y-80.0 Z-20.0 F100"]
    assert controller.get_internal_position() == Position(x=-90.0, y=-80.0, z=-20.0)
