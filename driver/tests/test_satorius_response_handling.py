import logging

import pytest

from qubot_drivers.satorius import SatoriusController, SatoriusDeviceError
from qubot_drivers.serialcontroller import SerialController


def make_controller() -> SatoriusController:
    controller = object.__new__(SatoriusController)
    controller._logger = logging.getLogger("test.sartorius")
    controller._volume = 0
    controller._tip_attached = False
    controller._microliter_per_step = controller.MICROLITER_PER_STEP
    return controller


def test_execute_raises_on_sartorius_er2(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = make_controller()
    monkeypatch.setattr(
        SerialController,
        "execute",
        lambda self, command, value=None, timeout=None: "1er2",
    )

    with pytest.raises(SatoriusDeviceError, match="out-of-bounds"):
        controller.execute(command="RO", value="200")


def test_custom_volume_conversion_maps_1000_ul_to_400_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SerialController, "__init__", lambda self, *args, **kwargs: None)
    controller = SatoriusController(microliter_per_step=2.5)
    commands: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        controller,
        "execute",
        lambda command, value=None, timeout=None: commands.append((command, value)) or "ok",
    )

    controller.aspirate(1000)

    assert commands == [("RI", "400")]


def test_full_volume_dispense_uses_blowout(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = make_controller()
    controller._volume = 100
    commands: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        controller,
        "execute",
        lambda command, value=None: commands.append((command, value)) or "1ok",
    )

    controller.dispense(100)

    assert commands == [("RB", None)]
    assert controller._volume == 0


def test_partial_dispense_uses_relative_outward_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = make_controller()
    controller._volume = 100
    commands: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        controller,
        "execute",
        lambda command, value=None: commands.append((command, value)) or "1ok",
    )

    controller.dispense(40)

    assert commands == [("RO", "80")]
    assert controller._volume == 60
