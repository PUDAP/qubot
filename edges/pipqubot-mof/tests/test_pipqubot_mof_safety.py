from puda.command import get_safety

from _pipqubot_mof_edge_driver import PipQuBotMOF

MOTION = (
    "home",
    "move_to_well",
    "move_z_relative",
    "attach_tip",
    "drop_tip",
    "aspirate_from",
    "dispense_to",
    "blowout",
)


def test_only_reconcile_tip_attached_requires_confirmation():
    assert get_safety(PipQuBotMOF.reconcile_tip_attached).confirm is True
    for name in MOTION:
        safety = get_safety(getattr(PipQuBotMOF, name))
        assert safety is not None
        assert safety.confirm is False
