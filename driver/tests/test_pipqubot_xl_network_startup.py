"""PipQuBot XL network-controller and motion-free startup tests."""

import asyncio

from qubot_drivers import Position

from qubot_drivers.machines import pipqubot_XL as module


class FakeQubot:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def set_axis_limits(self, axis, minimum, maximum):
        self.calls.append(("set_axis_limits", axis, minimum, maximum))

    def connect(self):
        self.calls.append(("connect",))

    def home(self):
        self.calls.append(("home",))

    def get_position(self):
        return Position(x=1.0, y=2.0, z=3.0, a=4.0)


class FakePipette:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def connect(self):
        self.calls.append(("connect",))

    def initialize(self):
        self.calls.append(("initialize",))

    def get_position(self):
        return 12


def test_xl_uses_http_controller_when_qubot_ip_is_configured(monkeypatch):
    monkeypatch.setattr(module, "RepRapHTTPController", FakeQubot, raising=False)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)

    machine = module.PipQuBotXL(
        qubot_ip="192.168.2.224",
        satorius_port="/dev/pipette",
    )

    assert isinstance(machine.qubot, FakeQubot)
    assert machine.qubot.kwargs == {"host": "192.168.2.224"}


def test_xl_uses_brl1000_microliters_per_step(monkeypatch):
    monkeypatch.setattr(module, "RepRapHTTPController", FakeQubot, raising=False)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)

    machine = module.PipQuBotXL(
        qubot_ip="192.168.2.224",
        satorius_port="/dev/pipette",
    )

    assert machine.MICROLITER_PER_STEP == 2.5
    assert getattr(machine.pipette, "kwargs")["microliter_per_step"] == 2.5


def test_xl_scale_emits_ri40_for_100ul_and_ri400_for_1000ul(monkeypatch):
    from qubot_drivers.satorius import SatoriusController

    sent = []

    def capture(command, value=None, timeout=None):
        sent.append((command, value))
        return "1ok"

    controller = SatoriusController(
        port_name="/dev/pipette",
        microliter_per_step=module.PipQuBotXL.MICROLITER_PER_STEP,
    )
    monkeypatch.setattr(controller, "execute", capture)

    controller.aspirate(100)
    controller.aspirate(1000)

    assert sent == [("RI", "40"), ("RI", "400")]
    assert SatoriusController.MICROLITER_PER_STEP == 0.5


def test_motion_free_startup_connects_without_homing_or_pipette_initialization(monkeypatch):
    monkeypatch.setattr(module, "RepRapHTTPController", FakeQubot, raising=False)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)
    machine = module.PipQuBotXL(
        qubot_ip="192.168.2.224",
        satorius_port="/dev/pipette",
    )

    machine.startup(home_gantry=False, initialize_pipette=False)

    assert machine.qubot.calls[-1] == ("connect",)
    assert ("home",) not in machine.qubot.calls
    assert machine.pipette.calls == [("connect",)]


def test_get_position_accepts_synchronous_http_controller(monkeypatch):
    monkeypatch.setattr(module, "RepRapHTTPController", FakeQubot, raising=False)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)
    machine = module.PipQuBotXL(
        qubot_ip="192.168.2.224",
        satorius_port="/dev/pipette",
    )

    result = asyncio.run(machine.get_position())

    assert result == {
        "qubot": {"x": 1.0, "y": 2.0, "z": 3.0, "a": 4.0},
        "pipette": 12,
    }
