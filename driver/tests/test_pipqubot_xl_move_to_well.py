from unittest.mock import Mock
import pytest
from qubot_drivers.machines.pipqubot_XL import PipQuBotXL
from qubot_drivers.position import Position


@pytest.fixture(autouse=True)
def block_hardware(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Hardware access is forbidden in positioning tests')

    monkeypatch.setattr('serial.Serial', forbidden)
    monkeypatch.setattr('urllib.request.urlopen', forbidden)


def test_move_to_well_keeps_command_safety_requirements():
    command = PipQuBotXL.move_to_well
    safety = getattr(command, '__puda_safety__')
    assert getattr(command, '__puda_command__') is True
    assert safety.hazards == ('collision', 'pinch point')
    assert safety.requires == (
        'Gantry homed, correct labware loaded, physical and software tip state consistent, and path clear.'
    )
    assert safety.confirm is False
    assert safety.forbidden_when is None


@pytest.mark.parametrize(('attached', 'height'), [(False, 21.0), (True, 21.0), (True, 0.0)])
def test_move_to_well_positions_at_bioshake_bottom_height(attached, height):
    # Construction only; the real controller validates, but motion is faked.
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.load_labware('B1', 'bioshake')
    machine.pipette.set_tip_attached(attached)
    top = machine._get_absolute_z_position('B1', 'A1')
    expected = top + Position(z=height) - Position(z=machine.deck['B1'].get_insert_depth())
    machine.qubot._execute_move = Mock(return_value=expected)
    machine.pipette.execute = Mock(side_effect=AssertionError('No pipette commands allowed'))
    for name in ('attach_tip', 'drop_tip', 'aspirate_from', 'dispense_to', 'blowout'):
        setattr(machine, name, Mock(side_effect=AssertionError('Positioning only')))

    result = machine.move_to_well(deck_slot='b1', well_name='A1', height_from_bottom=height)

    assert result == expected.to_dict()
    assert result['x'] == top.x
    assert result['y'] == top.y
    machine.qubot._execute_move.assert_called_once()
    commanded = machine.qubot._execute_move.call_args.kwargs['position']
    assert commanded.to_dict() == expected.to_dict()
    machine.pipette.execute.assert_not_called()
    assert machine.pipette.is_tip_attached() == attached
    for name in ('attach_tip', 'drop_tip', 'aspirate_from', 'dispense_to', 'blowout'):
        getattr(machine, name).assert_not_called()


@pytest.mark.parametrize('height', [-0.1, float('nan'), float('inf'), -float('inf')])
def test_move_to_well_rejects_invalid_height_before_motion(height):
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.load_labware('B1', 'bioshake')
    machine.qubot.move_absolute = Mock()
    machine.pipette.execute = Mock(side_effect=AssertionError('No pipette commands allowed'))

    with pytest.raises(ValueError, match='height_from_bottom.*finite.*non-negative'):
        machine.move_to_well(deck_slot='B1', well_name='A1', height_from_bottom=height)

    machine.qubot.move_absolute.assert_not_called()
    machine.pipette.execute.assert_not_called()


@pytest.mark.parametrize('attached', [False, True])
@pytest.mark.parametrize('height_kwargs', [{}, {'height_from_bottom': None}])
def test_move_to_well_positions_head_without_liquid_handling(attached, height_kwargs):
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.load_labware('A3', 'polyelectric_8_wellplate_30000ul')
    machine.pipette.set_tip_attached(attached)
    expected = machine._get_absolute_z_position('A3', 'A1')
    machine.qubot.move_absolute = Mock(return_value=expected)
    machine.pipette.execute = Mock(side_effect=AssertionError('No pipette commands allowed'))
    result = machine.move_to_well(deck_slot='a3', well_name='A1', **height_kwargs)
    commanded = machine.qubot.move_absolute.call_args.kwargs['position']
    assert commanded.to_dict() == expected.to_dict()
    assert result == expected.to_dict()
    machine.qubot.move_absolute.assert_called_once()
    machine.pipette.execute.assert_not_called()
    assert machine.pipette.is_tip_attached() == attached


@pytest.mark.parametrize('height', [None, 21.0])
def test_move_to_well_rejects_empty_slot_before_motion(height):
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.qubot.move_absolute = Mock()
    with pytest.raises(ValueError, match='No labware loaded'):
        machine.move_to_well(deck_slot='A3', well_name='A1', height_from_bottom=height)
    machine.qubot.move_absolute.assert_not_called()


@pytest.mark.parametrize('transport', ['http', 'serial'])
@pytest.mark.parametrize(('attached', 'height'), [(False, 0.0), (False, 1000.0), (True, 1000.0)])
def test_move_to_well_rejects_destination_outside_controller_z_limits(transport, attached, height):
    machine = PipQuBotXL(
        qubot_ip='unused' if transport == 'http' else None,
        qubot_port='unused' if transport == 'serial' else None,
        satorius_port='unused',
    )
    machine.load_labware('B1', 'bioshake')
    machine.pipette.set_tip_attached(attached)
    machine.qubot._execute_move = Mock()

    with pytest.raises(ValueError, match='outside axis limits'):
        machine.move_to_well(deck_slot='B1', well_name='A1', height_from_bottom=height)

    machine.qubot._execute_move.assert_not_called()


@pytest.mark.parametrize('transport', ['http', 'serial'])
def test_move_to_well_uses_configured_controller_z_limits(transport):
    machine = PipQuBotXL(
        qubot_ip='unused' if transport == 'http' else None,
        qubot_port='unused' if transport == 'serial' else None,
        satorius_port='unused',
    )
    machine.load_labware('B1', 'bioshake')
    machine.qubot.set_axis_limits('Z', -150, 0)
    machine.qubot._execute_move = Mock()

    with pytest.raises(ValueError, match='outside axis limits'):
        machine.move_to_well(deck_slot='B1', well_name='A1', height_from_bottom=21.0)

    machine.qubot._execute_move.assert_not_called()


@pytest.mark.parametrize('height', [None, 21.0])
@pytest.mark.parametrize(('slot', 'well'), [('Z9', 'A1'), ('B1', 'Z99')])
def test_move_to_well_rejects_unknown_slot_or_well_before_motion(height, slot, well):
    machine = PipQuBotXL(qubot_ip='unused', satorius_port='unused')
    machine.load_labware('B1', 'bioshake')
    machine.qubot.move_absolute = Mock()

    with pytest.raises(KeyError):
        machine.move_to_well(deck_slot=slot, well_name=well, height_from_bottom=height)

    machine.qubot.move_absolute.assert_not_called()
