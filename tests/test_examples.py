"""Every machine example in the qubot-driver skill builds a PUDA Driver without hardware."""

import importlib.util
import inspect
from pathlib import Path

import pytest
from puda.command import build_command_catalog, get_safety, is_command, require_command_names

from qubot.end_effector.orion_4ch_led import LedBoard
from qubot.end_effector.parallel_force_actuator import Finger
from qubot.gantry import Frame
from qubot.gantry.reprap_http import RepRapHTTPController
from qubot.serialcontroller import SerialController

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "skills" / "qubot-driver" / "references" / "examples").glob("*.py"))
BASIC = {"home", "move_absolute", "move_relative", "get_position"}
MOTION = {"home", "move_absolute", "move_relative"}


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"example_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def no_ports(monkeypatch):
    """Replace every open/close with a no-op so Driver() runs without hardware."""
    for cls in (SerialController, RepRapHTTPController, LedBoard, Finger):
        monkeypatch.setattr(cls, "connect", lambda self: None)
        monkeypatch.setattr(cls, "disconnect", lambda self: None)
    monkeypatch.setattr(LedBoard, "off", lambda self: "0;0;0;0\n")


def _ports(driver_cls) -> dict:
    values = {
        "gantry_port": "/dev/null",
        "gantry_host": "localhost",
        "pipette_port": "/dev/null",
        "led_port": "/dev/null",
        "finger_ports": ["/dev/null"] * 4,
    }
    names = [name for name in inspect.signature(driver_cls).parameters]
    return {name: values[name] for name in names}


def test_there_is_one_example_per_known_machine():
    assert [path.stem for path in EXAMPLES] == [
        "claw_machine",
        "dancefloor",
        "eis_qubot",
        "miniqubot",
        "overkill2",
        "photoreactor",
        "pipqubot_mof",
        "pipqubot_xl",
        "syringequbot",
    ]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_driver_builds_and_advertises(path, no_ports):
    example = _load(path)
    assert isinstance(example.FRAME, Frame)
    driver = example.Driver(**_ports(example.Driver))

    names = require_command_names(driver)
    assert BASIC <= set(names)
    for name in MOTION:
        meta = get_safety(getattr(driver, name))
        assert meta is not None and meta.confirm is True
    text, catalog = build_command_catalog(driver)
    assert {entry["name"] for entry in catalog} >= BASIC
    assert callable(driver.estop) and not is_command(driver.estop)

    for axis, (low, high) in example.FRAME.check_limits(example.SOFT_LIMITS).items():
        if low != high:
            limits = driver._gantry.get_axis_limits(axis)
            assert (limits.min, limits.max) == (low, high)
    assert driver.shutdown() is True
