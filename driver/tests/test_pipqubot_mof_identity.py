def test_mof_driver_has_distinct_class_identity():
    from qubot_drivers.machines.pipqubot_mof import PipQuBotMOF

    assert PipQuBotMOF.__name__ == "PipQuBotMOF"
    assert PipQuBotMOF.__module__ == "qubot_drivers.machines.pipqubot_mof"


def test_mof_uses_2_5_microliters_per_sartorius_step(monkeypatch):
    import qubot_drivers.machines.pipqubot_mof as module

    class FakeQubot:
        def __init__(self, **kwargs):
            pass

        def set_axis_limits(self, *args):
            pass

    class FakePipette:
        def __init__(self, **kwargs):
            self.microliter_per_step = kwargs.get("microliter_per_step")

    monkeypatch.setattr(module, "GrblHALController", FakeQubot)
    monkeypatch.setattr(module, "SatoriusController", FakePipette)

    machine = module.PipQuBotMOF(qubot_port="qubot", satorius_port="pipette")

    assert machine.pipette.microliter_per_step == 2.5
