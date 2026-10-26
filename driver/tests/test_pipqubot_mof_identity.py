from qubot_drivers.rline import RLineModel


def test_mof_driver_has_distinct_class_identity():
    from qubot_drivers.machines.pipqubot_mof import PipQuBotMOF

    assert PipQuBotMOF.__name__ == "PipQuBotMOF"
    assert PipQuBotMOF.__module__ == "qubot_drivers.machines.pipqubot_mof"


def test_mof_uses_50_1000_rline_model(monkeypatch):
    import qubot_drivers.machines.pipqubot_mof as module

    class FakeQubot:
        def __init__(self, **kwargs):
            pass

        def set_axis_limits(self, *args):
            pass

    class FakePipette:
        def __init__(self, **kwargs):
            self.model = kwargs.get("model")

    monkeypatch.setattr(module, "GrblHALController", FakeQubot)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)

    machine = module.PipQuBotMOF(qubot_port="qubot", satorius_port="pipette")

    assert machine.PIPETTE_MODEL is RLineModel.UL_50_1000
    assert machine.pipette.model is RLineModel.UL_50_1000
