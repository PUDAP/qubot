"""Configuration tests for the PipQuBot XL edge entrypoint."""

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("pipqubot_xl_edge_main", MODULE_PATH)
assert SPEC and SPEC.loader
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


class FakeDriver:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.startup_kwargs = None

    def startup(self, **kwargs):
        self.startup_kwargs = kwargs


def test_build_driver_uses_network_controller_without_startup_motion(monkeypatch):
    monkeypatch.setattr(main, "PipQuBotXL", FakeDriver)
    config = main.Config(
        machine_id="pipqubot-xl",
        nats_servers="nats://localhost:4222",
        qubot_ip="192.168.2.224",
        satorius_port="/dev/pipette",
        home_gantry_on_startup=False,
        initialize_pipette_on_startup=False,
    )

    driver = main.build_driver(config)

    assert driver.kwargs == {
        "qubot_ip": "192.168.2.224",
        "satorius_port": "/dev/pipette",
    }
    assert driver.startup_kwargs == {
        "home_gantry": False,
        "initialize_pipette": False,
    }
