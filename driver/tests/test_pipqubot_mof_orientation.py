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


def test_polyelectric_updated_depth_sets_one_mm_target():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("B2", "polyelectric_8_wellplate_30000ul")
    machine.pipette.set_tip_attached(attached=True)

    top = machine._get_absolute_z_position("B2", "A1")
    one_mm_above_bottom = top.z - machine.deck["B2"].get_insert_depth() + 1.0

    assert machine.deck["B2"].get_insert_depth() == pytest.approx(76.0)
    assert machine.deck["B2"]._definition["wells"]["A1"]["depth"] == pytest.approx(77.0)
    assert top.x == pytest.approx(128.2)
    assert top.y == pytest.approx(-283.2)
    assert top.z == pytest.approx(-54.0)
    assert one_mm_above_bottom == pytest.approx(-129.0)


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


def test_bioshake_b1_a1_uses_updated_geometry():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("B1", "bioshake")
    machine.pipette.set_tip_attached(attached=True)

    position = machine._get_absolute_z_position("B1", "A1")

    assert position.x == pytest.approx(12.44)
    assert position.y == pytest.approx(-288.32)
    assert position.z == pytest.approx(-15.0)


def test_bioshake_supports_dispense_depth():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("B1", "bioshake")

    assert machine.deck["B1"].get_insert_depth() == pytest.approx(43.8)


@pytest.mark.parametrize(
    ("labware_name", "expected"),
    [
        ("trash_bin_create", (42.2, -66.2, -118.0)),
        ("trash_bin_mof", (43.5, -1.2, -37.0)),
    ],
)
def test_trash_bin_d1_targets_are_inside_axis_limits(labware_name, expected):
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("D1", labware_name)
    machine.pipette.set_tip_attached(attached=True)

    position = machine._get_absolute_z_position("D1", "A1")

    assert position.x == pytest.approx(expected[0])
    assert position.y == pytest.approx(expected[1])
    assert position.z == pytest.approx(expected[2])
    assert 0 <= position.x <= 161.7
    assert -444 <= position.y <= 0
    assert -175 <= position.z <= 0


def test_trash_bin_mof_assumes_physical_tip_when_software_state_is_cleared():
    machine = PipQuBotMOF(
        qubot_port="/dev/does-not-open-in-this-test",
        satorius_port="/dev/does-not-open-in-this-test",
    )
    machine.load_labware("D1", "trash_bin_mof")

    assert machine.pipette.is_tip_attached() is False

    position = machine._get_absolute_z_position("D1", "A1")

    assert position.x == pytest.approx(43.5)
    assert position.y == pytest.approx(-1.2)
    assert position.z == pytest.approx(-37.0)
