import pytest

from qubot_drivers import Position
from qubot_drivers.machines.pipqubot_mof import PipQuBotMOF


def test_mof_tiprack_rows_match_physical_a_to_h_orientation():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("C1", "sartorious_96_tiprack_1000ul")

    a1 = machine._get_absolute_z_position("C1", "A1")
    h1 = machine._get_absolute_z_position("C1", "H1")

    assert a1.x == pytest.approx(11.35)
    assert h1.x == pytest.approx(74.35)
    assert a1.y == pytest.approx(-141.6)
    assert h1.y == pytest.approx(-141.6)
    assert a1.z == pytest.approx(-120.1)
    assert h1.z == pytest.approx(-120.1)


def test_move_to_well_positions_attached_tip_at_well_top():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("A2", "polyelectric_8_wellplate_30000ul")
    machine.pipette.set_tip_attached(attached=True)
    commanded = []
    machine.qubot.move_absolute = lambda position, feed=None: commanded.append(position.copy())

    result = machine.move_to_well(deck_slot="A2", well_name="A1")

    assert len(commanded) == 1
    assert commanded[0].x == pytest.approx(128.2)
    assert commanded[0].y == pytest.approx(-433.2)
    assert commanded[0].z == pytest.approx(-54.0)
    assert result == pytest.approx({"x": 128.2, "y": -433.2, "z": -54.0})


def test_move_z_relative_moves_only_z_and_returns_absolute_position():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    commanded = []

    def record_move(position, feed=None):
        commanded.append(position.copy())
        return Position(x=127.2, y=-433.2, z=-124.0)

    machine.qubot.move_relative = record_move

    result = machine.move_z_relative(distance_mm=-70.0)

    assert len(commanded) == 1
    assert not commanded[0].has_axis("x")
    assert not commanded[0].has_axis("y")
    assert commanded[0].z == pytest.approx(-70.0)
    assert result == pytest.approx({"x": 127.2, "y": -433.2, "z": -124.0})
