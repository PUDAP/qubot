import math
from pathlib import Path

import pytest
from puda import EdgeNatsClient, EdgeRunner
from puda.command import get_safety, resolve_command_names
from puda.machine_state import find_machine_state_handler
from puda.tlm_stream import get_tlm_stream_spec

from qubot_drivers.move.grblHAL import GrblHALController, GrblStatusReport
from qubot_drivers.position import Position
from qubot_drivers.machines.miniqubot import AXIS_LIMITS, EXPECTED_IDENTITY, MiniQubot


SETTINGS = "\n".join(
    [
        "$20=1",
        "$21=1",
        "$22=1",
        "$23=1",
        "$110=1500.000",
        "$111=1500.000",
        "$112=200.000",
        "$130=175.000",
        "$131=190.000",
        "$132=75.000",
        "ok",
    ]
)


class FakeController:
    def __init__(self, position=(0.0, 0.0, 0.0), state="Idle"):
        self.calls = []
        self.position = position
        self.state = state
        self.identity = f"{EXPECTED_IDENTITY}\n[OPT:VZH,15,128]\nok"
        self.settings = SETTINGS
        self.connected = False

    def connect(self):
        self.calls.append("connect")
        self.connected = True

    def disconnect(self):
        self.calls.append("disconnect")
        self.connected = False

    def get_info(self):
        self.calls.append("get_info")
        return self.identity

    def execute(self, command, **_kwargs):
        self.calls.append(command)
        return self.settings

    def set_axis_limits(self, axis, minimum, maximum):
        self.calls.append(("limits", axis, minimum, maximum))

    def home(self, axis=None, *, verify_origin=False):
        self.calls.append(("home", axis, verify_origin))

    def read_status(self):
        self.calls.append("read_status")
        x, y, z = self.position
        raw = f"<{self.state}|MPos:{x},{y},{z}|FS:0,0>"
        return GrblStatusReport(state=self.state, position=Position(x=x, y=y, z=z), raw=raw)

    def move_absolute(self, position, feed=None, *, apply_safe_z=True, timeout=None):
        self.calls.append(
            ("move", position.x, position.y, position.z, feed, apply_safe_z, timeout)
        )
        self.position = (position.x, position.y, position.z)


def test_package_exports_miniqubot():
    from qubot_drivers.machines import MiniQubot as exported

    assert exported is MiniQubot


def test_startup_checks_identity_then_homes():
    controller = FakeController()
    machine = MiniQubot(controller=controller)

    machine.startup()

    assert controller.calls[:3] == ["connect", "get_info", "$$"]
    assert ("home", None, True) in controller.calls
    assert machine._homed is True


def test_startup_does_not_home_when_identity_mismatches():
    controller = FakeController()
    controller.identity = "[VER:1.1f:]\nok"
    machine = MiniQubot(controller=controller)

    with pytest.raises(RuntimeError, match="identity"):
        machine.startup()

    assert ("home", None, True) not in controller.calls
    assert machine._homed is False


def test_startup_does_not_home_when_travel_settings_mismatch():
    controller = FakeController()
    controller.settings = SETTINGS.replace("$130=175.000", "$130=10.000")
    machine = MiniQubot(controller=controller)

    with pytest.raises(RuntimeError, match="settings"):
        machine.startup()

    assert ("home", None, True) not in controller.calls


def test_omitted_feed_uses_each_axis_maximum():
    controller = FakeController(position=(10.0, -10.0, -5.0))
    machine = MiniQubot(controller=controller)
    machine._homed = True

    machine.move_absolute(20, -30, -5)
    machine.move_absolute(20, -30, -15)
    machine.move_absolute(25, -40, -25)

    moves = [call for call in controller.calls if isinstance(call, tuple) and call[0] == "move"]
    assert [move[1:5] for move in moves] == [
        (20.0, -30.0, -5.0, 1500.0),
        (20.0, -30.0, -15.0, 200.0),
        (25.0, -40.0, -15.0, 1500.0),
        (25.0, -40.0, -25.0, 200.0),
    ]


def test_specified_combined_feed_is_used_on_both_legs():
    controller = FakeController()
    machine = MiniQubot(controller=controller)
    machine._homed = True

    result = machine.move_absolute(10, -10, -5, feed_mm_min=100)

    moves = [call for call in controller.calls if isinstance(call, tuple) and call[0] == "move"]
    assert [move[1:5] for move in moves] == [
        (10.0, -10.0, 0.0, 100.0),
        (10.0, -10.0, -5.0, 100.0),
    ]
    assert all(move[5] is False for move in moves)
    assert result == {"x": 10.0, "y": -10.0, "z": -5.0}
    assert machine.snapshot() == {"homed": True, "position": result}


def test_move_is_refused_before_homing():
    controller = FakeController()
    machine = MiniQubot(controller=controller)

    with pytest.raises(RuntimeError, match="not homed"):
        machine.move_absolute(1, -1, -1)

    assert not any(call[0] == "move" for call in controller.calls if isinstance(call, tuple))


def test_relative_move_adds_a_fresh_position():
    controller = FakeController(position=(10.0, -20.0, -5.0))
    machine = MiniQubot(controller=controller)
    machine._homed = True

    machine.move_relative(1, -2, -3, feed_mm_min=100)

    moves = [call for call in controller.calls if isinstance(call, tuple) and call[0] == "move"]
    assert [move[1:5] for move in moves] == [
        (11.0, -22.0, -5.0, 100.0),
        (11.0, -22.0, -8.0, 100.0),
    ]


def test_miniqubot_is_not_a_pipette_or_capper_machine():
    machine = MiniQubot(controller=FakeController())

    assert type(machine).__name__ == "MiniQubot"
    assert not hasattr(machine, "pipette")
    assert not hasattr(machine, "deck")
    assert resolve_command_names(machine) == {
        "get_position",
        "home",
        "move_absolute",
        "move_relative",
    }
    assert get_safety(MiniQubot.home).confirm is False
    assert get_safety(MiniQubot.move_absolute).confirm is False
    assert get_safety(MiniQubot.move_relative).confirm is False
    assert get_safety(MiniQubot.shutdown) is None


def test_startup_installs_axis_limits_before_homing():
    controller = FakeController()
    MiniQubot(controller=controller).startup()

    limit_calls = [call for call in controller.calls if isinstance(call, tuple) and call[0] == "limits"]
    home_index = controller.calls.index(("home", None, True))
    assert limit_calls == [
        ("limits", axis, minimum, maximum) for axis, (minimum, maximum) in AXIS_LIMITS.items()
    ]
    assert all(controller.calls.index(call) < home_index for call in limit_calls)


def test_get_position_returns_the_fresh_sample():
    controller = FakeController(position=(12.5, -3.0, -1.0))
    machine = MiniQubot(controller=controller)
    assert machine.get_position() == {
        "x": 12.5,
        "y": -3.0,
        "z": -1.0,
    }
    assert machine.snapshot()["position"] == {
        "x": 12.5,
        "y": -3.0,
        "z": -1.0,
    }


def test_position_stream_and_machine_state_are_cached():
    spec = get_tlm_stream_spec(MiniQubot.get_position)
    assert spec is not None
    assert spec.name == "pos"
    assert spec.interval == 3.0
    assert get_tlm_stream_spec(MiniQubot.snapshot) is None
    assert resolve_command_names(MiniQubot(controller=FakeController())) == {
        "get_position",
        "home",
        "move_absolute",
        "move_relative",
    }

    machine = MiniQubot(controller=FakeController(position=(1.0, -2.0, -3.0)))
    handler = find_machine_state_handler(machine)
    assert handler is not None
    assert handler() == {"homed": False, "position": None}
    machine.get_position()
    machine._homed = True
    assert handler() == {
        "homed": True,
        "position": {"x": 1.0, "y": -2.0, "z": -3.0},
    }


def test_edge_runner_advertises_the_position_stream():
    machine = MiniQubot(controller=FakeController())
    client = EdgeNatsClient(servers=["nats://127.0.0.1:4222"], machine_id="miniqubot")
    runner = EdgeRunner(nats_client=client, machine_driver=machine)

    assert client.sdk_version == "0.0.18"
    assert runner.telemetry_handler is None
    assert [(name, spec.interval) for name, _, spec in runner.tlm_streams] == [("pos", 3.0)]
    assert client.description == (
        "Three-axis empty-head Qubot on a GRBL serial controller."
    )
    assert client.state_handler() == {"homed": False, "position": None}
    assert "telemetry_handler" not in (
        Path(__file__).resolve().parents[2] / "miniqubot-edge" / "main.py"
    ).read_text()


def test_edge_package_requires_sdk_0_0_18_without_psutil():
    text = (Path(__file__).resolve().parents[2] / "miniqubot-edge" / "pyproject.toml").read_text()
    assert "puda>=0.0.18" in text
    assert "psutil" not in text


def test_move_rejects_alarm_and_non_finite_values_before_motion():
    controller = FakeController(state="Alarm")
    machine = MiniQubot(controller=controller)
    machine._homed = True

    with pytest.raises(RuntimeError, match="Alarm"):
        machine.move_absolute(1, -1, -1)
    assert not any(isinstance(call, tuple) and call[0] == "move" for call in controller.calls)

    with pytest.raises(ValueError, match="finite"):
        machine.move_absolute(math.nan, 0, 0)
    with pytest.raises(ValueError, match="feed_mm_min"):
        machine.move_relative(1, 0, 0, feed_mm_min=0)


def test_relative_move_is_refused_before_homing():
    machine = MiniQubot(controller=FakeController(position=(5.0, -5.0, -5.0)))

    with pytest.raises(RuntimeError, match="not homed"):
        machine.move_relative(1, 0, 0)


def test_failed_move_and_position_mismatch_clear_homing():
    controller = FakeController()

    def fail_move(*_args, **_kwargs):
        raise RuntimeError("controller rejected G1")

    controller.move_absolute = fail_move
    machine = MiniQubot(controller=controller)
    machine._homed = True
    with pytest.raises(RuntimeError, match="rejected"):
        machine.move_absolute(1, -1, -1)
    assert machine._homed is False

    controller = FakeController()
    controller.move_absolute = lambda position, feed=None, *, apply_safe_z=True, timeout=None: None
    machine = MiniQubot(controller=controller)
    machine._homed = True
    with pytest.raises(RuntimeError, match="away from the requested target"):
        machine.move_absolute(10, -10, -5)
    assert machine._homed is False


def test_specified_feed_is_not_replaced_by_the_axis_maximum():
    controller = FakeController()
    machine = MiniQubot(controller=controller)
    machine._homed = True

    machine.move_absolute(10, -10, -5, feed_mm_min=1000)
    machine.move_absolute(12, -10, -5, feed_mm_min=400)
    machine.move_absolute(12, -10, -8, feed_mm_min=50)

    moves = [call for call in controller.calls if isinstance(call, tuple) and call[0] == "move"]
    assert [move[4] for move in moves] == [1000.0, 1000.0, 400.0, 50.0]


def test_shutdown_disconnects_and_drops_homing():
    controller = FakeController()
    machine = MiniQubot(controller=controller)
    machine._homed = True

    machine.shutdown()

    assert controller.calls == ["disconnect"]
    assert machine._homed is False


def test_out_of_range_target_is_rejected_by_the_shared_grbl_limits():
    controller = GrblHALController(port_name="/dev/not-opened-in-unit-tests")
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"
    controller.read_status = lambda: GrblStatusReport(
        state="Idle",
        position=Position(x=0.0, y=0.0, z=0.0),
        raw="<Idle|MPos:0,0,0>",
    )
    machine = MiniQubot(controller=controller)
    machine._homed = True
    for axis, (minimum, maximum) in AXIS_LIMITS.items():
        controller.set_axis_limits(axis, minimum, maximum)

    with pytest.raises(ValueError, match="outside axis limits"):
        machine.move_absolute(176, 0, 0)

    assert commands == []
    assert machine._homed is True


def test_deadline_rejection_keeps_homing_and_sends_no_move():
    controller = FakeController()
    machine = MiniQubot(controller=controller)
    machine._homed = True

    with pytest.raises(ValueError, match="deadline"):
        machine.move_absolute(175, -190, -75, feed_mm_min=0.1)

    assert machine._homed is True
    assert not any(isinstance(call, tuple) and call[0] == "move" for call in controller.calls)


def test_axis_endpoints_accept_max_xyz_feed_and_xy_max_rate():
    controller = GrblHALController(port_name="/dev/not-opened-in-unit-tests")
    commands = []
    controller.execute = lambda command, **_kwargs: commands.append(command) or "ok"
    controller._wait_for_move = lambda timeout=None: None
    controller._current_position = Position(x=0.0, y=0.0, z=0.0)
    for axis, (minimum, maximum) in AXIS_LIMITS.items():
        controller.set_axis_limits(axis, minimum, maximum)

    controller.move_absolute(
        Position(x=175.0, y=-190.0, z=-75.0),
        feed=200,
        apply_safe_z=False,
    )
    endpoint = next(command for command in commands if command.startswith("G1"))
    assert "X175.0" in endpoint
    assert "Y-190.0" in endpoint
    assert "Z-75.0" in endpoint
    assert endpoint.endswith("F200")

    commands.clear()
    controller._current_position = Position(x=0.0, y=0.0, z=0.0)
    controller.move_absolute(
        Position(x=40.0, y=-40.0, z=0.0),
        feed=1500,
        apply_safe_z=False,
    )
    xy_move = next(command for command in commands if command.startswith("G1"))
    assert "X40.0" in xy_move
    assert "Y-40.0" in xy_move
    assert "Z" not in xy_move
    assert xy_move.endswith("F1500")
