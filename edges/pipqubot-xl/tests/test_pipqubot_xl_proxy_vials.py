"""PipQuBot XL proxy-vial transfer support; all hardware access is faked."""
from unittest.mock import Mock

import pytest

from _pipqubot_xl_edge_driver import PipQuBotXL
from qubot_drivers.position import Position


@pytest.fixture(autouse=True)
def block_hardware(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Hardware access is forbidden in proxy-vial tests")

    monkeypatch.setattr("serial.Serial", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("_pipqubot_xl_edge_driver.time.sleep", lambda _: None)


def make_machine() -> PipQuBotXL:
    machine = PipQuBotXL(qubot_ip="unused", satorius_port="unused")
    machine.qubot.move_absolute = Mock(side_effect=lambda position: position)
    machine.pipette.dispense = Mock(return_value=None)
    return machine


def test_x_limit_matches_operator_confirmed_345_mm():
    assert PipQuBotXL.DEFAULT_AXIS_LIMITS["X"] == (0, 345)


def test_proxy_b6_is_exact_measured_dispense_target_and_inside_limits():
    position = PipQuBotXL.PROXY_VIAL_POSITIONS["B6"]
    assert position.to_dict() == {"x": 338.0, "y": -210.0, "z": -28.5}
    assert PipQuBotXL.DEFAULT_AXIS_LIMITS["X"][0] <= position.x <= PipQuBotXL.DEFAULT_AXIS_LIMITS["X"][1]
    assert PipQuBotXL.DEFAULT_AXIS_LIMITS["Y"][0] <= position.y <= PipQuBotXL.DEFAULT_AXIS_LIMITS["Y"][1]
    assert PipQuBotXL.DEFAULT_AXIS_LIMITS["Z"][0] <= position.z <= PipQuBotXL.DEFAULT_AXIS_LIMITS["Z"][1]


def test_reconcile_tip_attached_requires_explicit_physical_confirmation():
    machine = make_machine()
    assert machine.pipette.is_tip_attached() is False

    with pytest.raises(ValueError, match="physical_tip_confirmed must be true"):
        machine.reconcile_tip_attached(physical_tip_confirmed=False)

    assert machine.pipette.is_tip_attached() is False
    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


def test_reconcile_tip_attached_sets_software_state_without_hardware_io():
    machine = make_machine()

    result = machine.reconcile_tip_attached(physical_tip_confirmed=True)

    assert result == {"tip_attached": True}
    assert machine.pipette.is_tip_attached() is True
    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


def test_dispense_to_proxy_vial_b6_uses_calibrated_absolute_target():
    machine = make_machine()
    machine.pipette.set_tip_attached(True)
    machine.pipette._volume = 1000

    result = machine.dispense_to_proxy_vial(well_name="b6", amount=1000)

    expected = Position(x=338.0, y=-210.0, z=-28.5)
    commanded = machine.qubot.move_absolute.call_args.kwargs["position"]
    assert commanded.to_dict() == expected.to_dict()
    machine.pipette.dispense.assert_called_once_with(amount=1000)
    assert result == {
        "well_name": "B6",
        "amount": 1000,
        "x": 338.0,
        "y": -210.0,
        "z": -28.5,
        "calibration_id": "70792568-cf46-493a-8ce6-5fdf08025df6",
    }


def test_dispense_to_proxy_vial_rejects_untracked_volume_before_motion():
    machine = make_machine()
    machine.pipette.set_tip_attached(True)
    machine.pipette._volume = 0

    with pytest.raises(ValueError, match="exceeds tracked aspirated volume"):
        machine.dispense_to_proxy_vial(well_name="B6", amount=1000)

    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


@pytest.mark.parametrize("well_name", ["", "C1", "A0", "B7"])
def test_dispense_to_proxy_vial_rejects_unknown_well_before_motion(well_name):
    machine = make_machine()
    machine.pipette.set_tip_attached(True)

    with pytest.raises(KeyError, match="Unknown proxy vial well"):
        machine.dispense_to_proxy_vial(well_name=well_name, amount=1000)

    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


def test_dispense_to_proxy_vial_requires_attached_tip_before_motion():
    machine = make_machine()

    with pytest.raises(ValueError, match="Tip not attached"):
        machine.dispense_to_proxy_vial(well_name="B6", amount=1000)

    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


@pytest.mark.parametrize("amount", [0, -1])
def test_dispense_to_proxy_vial_rejects_nonpositive_amount_before_motion(amount):
    machine = make_machine()
    machine.pipette.set_tip_attached(True)

    with pytest.raises(ValueError, match="positive"):
        machine.dispense_to_proxy_vial(well_name="B6", amount=amount)

    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.dispense.assert_not_called()


def test_proxy_commands_publish_confirmation_safety_metadata():
    reconcile_safety = getattr(PipQuBotXL.reconcile_tip_attached, "__puda_safety__")
    dispense_safety = getattr(PipQuBotXL.dispense_to_proxy_vial, "__puda_safety__")
    assert reconcile_safety.confirm is True
    # XL liquid transfers have an operator-approved per-action confirmation waiver.
    assert dispense_safety.confirm is False
    assert "collision" in dispense_safety.hazards
    assert "chemical exposure" in dispense_safety.hazards
    assert "capper A-axis motion" in dispense_safety.hazards
    assert "capper A axis homed" in dispense_safety.requires
    assert "capper and tip transit paths clear" in dispense_safety.requires
