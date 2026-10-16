import pytest
from qubot_drivers.machines.pipqubot_XL import PipQuBotXL


def test_sartorius_rows_follow_operator_verified_physical_orientation():
    # Construct only: no connect, startup, serial access, or motion.
    machine = PipQuBotXL(qubot_ip="unused", satorius_port="unused")
    machine.load_labware("B3", "sartorious_96_tiprack_1000ul")
    origin = machine.SLOT_ORIGINS["B3"]
    for column in (1, 12):
        for row_index, row in enumerate("ABCDEFGH"):
            position = machine._get_absolute_z_position("B3", f"{row}{column}")
            assert position.x == pytest.approx(origin.x + 11.15 + 9 * row_index)
            assert position.y == pytest.approx(origin.y + 14.6 + 9 * (column - 1))
            assert position.z == pytest.approx(
                machine.deck["B3"].get_height() - machine.CEILING_HEIGHT
            )
