from qubot.end_effector import rline_5_200
from qubot.end_effector.rline import RLINE_SPECS, RLineModel


def test_rline_5_200_identity_and_spec():
    assert rline_5_200.MODEL is RLineModel.UL_5_200
    assert rline_5_200.COMMUNICATION == "serial"
    assert rline_5_200.MICROLITERS_PER_STEP == 0.5

    spec = RLINE_SPECS[rline_5_200.MODEL]
    assert spec.minimum_volume_ul == 5
    assert spec.maximum_volume_ul == 200
    assert spec.microliters_per_second == (31, 52, 80, 115, 150, 190)


def test_connect_locks_controller_to_5_200_model(monkeypatch):
    captured = {}

    class FakeController:
        def __init__(self, *, port_name, model):
            captured.update(port_name=port_name, model=model)

    monkeypatch.setattr(rline_5_200, "SatoriusController", FakeController)

    controller = rline_5_200.connect("COM7")

    assert isinstance(controller, FakeController)
    assert captured == {"port_name": "COM7", "model": RLineModel.UL_5_200}
