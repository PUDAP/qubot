"""Operator-observed XL BioShake A/D and B/C reversal; no hardware access."""
import pytest

from qubot_drivers.labware import StandardLabware
from qubot_drivers.machines.pipqubot_XL import PipQuBotXL
from qubot_drivers.position import Position


@pytest.mark.parametrize("attached", [False, True])
@pytest.mark.parametrize("column", range(1, 7))
@pytest.mark.parametrize("row_index,row", list(enumerate("ABCD")))
def test_xl_bioshake_rows_match_operator_verified_orientation(row_index, row, column, attached):
    machine = PipQuBotXL(qubot_ip="unused", satorius_port="unused")
    machine.load_labware("B1", "bioshake")
    machine.pipette.set_tip_attached(attached)
    origin = machine.SLOT_ORIGINS["B1"]
    position = machine._get_absolute_z_position("B1", f"{row}{column}")
    assert position.x == pytest.approx(origin.x + 12.24 + 18 * row_index)
    assert position.y == pytest.approx(origin.y + 17.88 + 18 * (column - 1))
    expected_z = 113 - machine.CEILING_HEIGHT + (machine.TIP_LENGTH if attached else 0)
    assert position.z == pytest.approx(expected_z)
    # Exactly the existing bottom-relative dispense/positioning calculation.
    destination = position + Position(z=21 - machine.deck["B1"].get_insert_depth())
    assert destination.z == pytest.approx(expected_z + 21 - 43.8)


def test_shared_bioshake_definition_remains_unchanged_for_other_machines():
    labware = StandardLabware("bioshake")
    for column in range(1, 7):
        for row_index, row in enumerate("ABCD"):
            position = labware.get_well_position(f"{row}{column}")
            assert position.x == pytest.approx(17.88 + 18 * (column - 1))
            assert position.y == pytest.approx(66.24 - 18 * row_index)
    assert labware.get_height() == 113
    assert labware.get_insert_depth() == 43.8
