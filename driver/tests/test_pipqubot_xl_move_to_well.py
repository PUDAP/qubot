from unittest.mock import Mock
import pytest
from qubot_drivers.machines.pipqubot_XL import PipQuBotXL


@pytest.mark.parametrize('attached', [False, True])
def test_move_to_well_positions_head_without_liquid_handling(attached):
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.load_labware('A3', 'polyelectric_8_wellplate_30000ul')
    machine.pipette.set_tip_attached(attached)
    expected = machine._get_absolute_z_position('A3', 'A1')
    machine.qubot.move_absolute = Mock(return_value=expected)
    machine.pipette.execute = Mock(side_effect=AssertionError('No pipette commands allowed'))
    result = machine.move_to_well(deck_slot='A3', well_name='A1')
    commanded = machine.qubot.move_absolute.call_args.kwargs['position']
    assert commanded.to_dict() == expected.to_dict()
    assert result == expected.to_dict()
    machine.qubot.move_absolute.assert_called_once()
    machine.pipette.execute.assert_not_called()
    assert machine.pipette.is_tip_attached() == attached


def test_move_to_well_rejects_empty_slot_before_motion():
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.qubot.move_absolute = Mock()
    with pytest.raises(ValueError, match='No labware loaded'):
        machine.move_to_well(deck_slot='A3', well_name='A1')
    machine.qubot.move_absolute.assert_not_called()
