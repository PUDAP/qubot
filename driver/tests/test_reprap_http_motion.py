from qubot_drivers.move.reprap_http import RepRapHTTPController
from qubot_drivers.position import Position


def configured_controller() -> RepRapHTTPController:
    controller = RepRapHTTPController("robot.local")
    for axis in controller.VALID_AXES:
        controller.set_axis_limits(axis, -100, 100)
    return controller


def test_move_absolute_uses_absolute_gcode_and_waits(monkeypatch) -> None:
    controller = configured_controller()
    commands: list[str] = []
    monkeypatch.setattr(controller, "execute", lambda command: commands.append(command) or {})
    monkeypatch.setattr(
        controller,
        "execute_and_wait",
        lambda command: commands.append(command) or {},
    )
    monkeypatch.setattr(controller, "get_position", lambda: Position(x=10, y=20))

    result = controller.move_absolute(Position(x=10, y=20), feed=1500)

    assert commands == ["G90", "G0X10.0Y20.0F1500"]
    assert result.to_dict() == {"x": 10.0, "y": 20.0}


def test_move_relative_converts_delta_to_bounded_absolute_move(monkeypatch) -> None:
    controller = configured_controller()
    commands: list[str] = []
    positions = iter([Position(x=10, y=20, z=30, a=0), Position(x=15, y=18, z=30, a=0)])
    monkeypatch.setattr(controller, "get_position", lambda: next(positions))
    monkeypatch.setattr(controller, "execute", lambda command: commands.append(command) or {})
    monkeypatch.setattr(
        controller,
        "execute_and_wait",
        lambda command: commands.append(command) or {},
    )

    result = controller.move_relative(Position(x=5, y=-2))

    assert commands == ["G90", "G0X15.0Y18.0"]
    assert result.to_dict() == {"x": 15.0, "y": 18.0, "z": 30.0, "a": 0.0}
