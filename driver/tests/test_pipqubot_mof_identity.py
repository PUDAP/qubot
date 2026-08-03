def test_mof_driver_has_distinct_class_identity():
    from qubot_drivers.machines.pipqubot_mof import PipQuBotMOF

    assert PipQuBotMOF.__name__ == "PipQuBotMOF"
    assert PipQuBotMOF.__module__ == "qubot_drivers.machines.pipqubot_mof"
