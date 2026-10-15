import asyncio
import inspect

from qubot_drivers.move.reprap import RepRapController
from qubot_drivers.move.reprap_http import RepRapHTTPController
from qubot_drivers.position import Position


def configured_controller() -> RepRapHTTPController:
    controller = RepRapHTTPController("robot.local")
    for axis in controller.VALID_AXES:
        controller.set_axis_limits(axis, -100, 100)
    return controller


def test_http_controller_exposes_serial_controller_motion_api() -> None:
    public_serial_api = {
        name
        for name, value in RepRapController.__dict__.items()
        if not name.startswith("_") and (callable(value) or isinstance(value, property))
    }

    assert public_serial_api <= set(dir(RepRapHTTPController))
    assert hasattr(RepRapHTTPController, "_sync_position")
    assert inspect.iscoroutinefunction(RepRapHTTPController.get_position)


def test_move_absolute_uses_serial_safe_move_sequence(monkeypatch) -> None:
    controller = configured_controller()
    commands: list[str] = []
    monkeypatch.setattr(controller, "execute", lambda command: commands.append(command) or {})
    monkeypatch.setattr(controller, "_wait_for_move", lambda: commands.append("WAIT"))

    result = controller.move_absolute(Position(x=10, y=20), feed=1500)

    assert commands == [
        "G90",
        "G1 Z-5 A-5 F1000",
        "WAIT",
        "G1 X10.0 Y20.0 F1500",
        "WAIT",
        "G1 Z0.0 F1000",
        "WAIT",
        "G1 A0.0 F1000",
        "WAIT",
    ]
    assert result.to_dict() == {"x": 10.0, "y": 20.0, "z": 0.0, "a": 0.0}


def test_move_relative_uses_tracked_position_and_serial_safe_path(monkeypatch) -> None:
    controller = configured_controller()
    controller._current_position = Position(x=10, y=20, z=0, a=0)
    commands: list[str] = []
    monkeypatch.setattr(controller, "execute", lambda command: commands.append(command) or {})
    monkeypatch.setattr(controller, "_wait_for_move", lambda: commands.append("WAIT"))

    result = controller.move_relative(Position(x=5, y=-2))

    assert commands == [
        "G90",
        "G1 Z-5 A-5 F1000",
        "WAIT",
        "G1 X15.0 Y18.0 F3000",
        "WAIT",
        "G1 Z0.0 F1000",
        "WAIT",
        "G1 A0.0 F1000",
        "WAIT",
    ]
    assert result.to_dict() == {"x": 15.0, "y": 18.0, "z": 0.0, "a": 0.0}


def test_get_position_uses_http_status_asynchronously(monkeypatch) -> None:
    controller = configured_controller()
    monkeypatch.setattr(
        controller,
        "_get_status",
        lambda: {"coords": {"xyz": [1, 2, 3], "abc": [4]}},
    )

    result = asyncio.run(controller.get_position())

    assert result == Position(x=1, y=2, z=3, a=4)


def test_home_waits_and_resets_internal_position(monkeypatch) -> None:
    controller = configured_controller()
    controller._current_position = Position(x=10, y=20, z=-30, a=-40)
    commands: list[str] = []
    monkeypatch.setattr(controller, "execute", lambda command: commands.append(command) or {})
    monkeypatch.setattr(controller, "wait_for_idle", lambda: commands.append("WAIT"))

    controller.home(axis="z")

    assert commands == ["G28 Z", "WAIT"]
    assert controller.get_internal_position() == Position(x=10, y=20, z=0, a=-40)
