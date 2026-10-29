"""Offline tests for the syringe Qubot gantry."""

import pytest
from puda.command import get_safety, resolve_command_names

from _syringequbot_edge_driver import SyringeQubot
from qubot_drivers.position import Position


class FakeController:
    def __init__(self):
        self.calls = []

    def connect(self):
        self.calls.append("connect")

    def disconnect(self):
        self.calls.append("disconnect")

    def home(self, axis=None):
        self.calls.append(("home", axis))

    def g0(self, position):
        self.calls.append(("g0", dict(position._axes)))
        return {}

    def get_status(self):
        self.calls.append("get_status")
        return {"status": "I"}

    async def get_position(self):
        self.calls.append("get_position")
        return Position(x=1.0, y=-2.0, z=-3.0, a=4.0)

    def set_pin(self, pin, state):
        self.calls.append(("set_pin", pin, state))

    def set_axis_limits(self, axis, minimum, maximum):
        self.calls.append(("limits", axis, minimum, maximum))


def test_edge_driver_exports_syringequbot():
    from _syringequbot_edge_driver import SyringeQubot as exported

    assert exported is SyringeQubot


def test_startup_connects_without_homing():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)

    machine.startup()

    assert [call for call in controller.calls if call[0] == "limits"] == [
        ("limits", "X", 0.0, 140.0),
        ("limits", "Y", -170.0, 0.0),
        ("limits", "Z", -125.0, 0.0),
    ]
    assert controller.calls[-1] == "connect"
    assert machine._homed is False


def test_move_requires_home_and_sends_one_direct_move():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)
    machine.startup()

    with pytest.raises(RuntimeError, match="not homed"):
        machine.move_to(1, -2, -3)
    assert ("g0", {"x": 1.0, "y": -2.0, "z": -3.0}) not in controller.calls

    machine.home()
    result = machine.move_to(1, -2, -3)

    assert result == {"x": 1.0, "y": -2.0, "z": -3.0}
    assert ("g0", {"x": 1.0, "y": -2.0, "z": -3.0}) in controller.calls


def test_safe_move_retracts_to_z_zero_before_xy():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)
    machine._homed = True

    result = machine.safe_move_to(10, -20, -30)

    assert SyringeQubot.Z_SAFE == 0.0
    assert result == {"x": 10.0, "y": -20.0, "z": -30.0}
    assert [call for call in controller.calls if call[0] == "g0"] == [
        ("g0", {"z": 0.0}),
        ("g0", {"x": 10.0, "y": -20.0}),
        ("g0", {"z": -30.0}),
    ]


def test_home_and_reset_do_not_touch_clamp_pins():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)

    machine.home()
    machine.reset()

    assert not any(call[0] == "set_pin" for call in controller.calls)
    assert [call for call in controller.calls if call[0] == "home"] == [
        ("home", "Z"),
        ("home", "X"),
        ("home", "Y"),
        ("home", "Z"),
        ("home", "X"),
        ("home", "Y"),
    ]
    assert "disconnect" in controller.calls
    assert "connect" in controller.calls


def test_end_limits_reject_motion_before_transmission():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)
    machine._homed = True
    g0_calls = len([call for call in controller.calls if call[0] == "g0"])

    with pytest.raises(ValueError, match="X axis limits"):
        machine.move_to(141, -170, -125)
    with pytest.raises(ValueError, match="Y axis limits"):
        machine.safe_move_to(140, -171, -125)
    with pytest.raises(ValueError, match="Z axis limits"):
        machine.move_to(140, -170, -126)

    assert [call for call in controller.calls if call[0] == "g0"][g0_calls:] == []
    assert machine.move_to(140, -170, -125) == {"x": 140.0, "y": -170.0, "z": -125.0}


def test_position_reports_xyz_only():
    controller = FakeController()
    machine = SyringeQubot(controller=controller)

    assert machine.get_position() == {"x": 1.0, "y": -2.0, "z": -3.0}


def test_advertised_commands_are_motion_only():
    machine = SyringeQubot(controller=FakeController())

    assert resolve_command_names(machine) == {
        "get_position",
        "get_status",
        "home",
        "move_to",
        "reset",
        "safe_move_to",
        "shutdown",
    }
    for method in (machine.home, machine.move_to, machine.safe_move_to, machine.reset):
        assert get_safety(method).confirm is True
