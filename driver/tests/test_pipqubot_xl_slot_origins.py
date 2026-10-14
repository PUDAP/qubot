from qubot_drivers.machines.pipqubot_XL import PipQuBotXL


def test_pipqubot_xl_slot_origins_match_calibrated_positions() -> None:
    expected = {
        "A1": (-5.3, -470.0),
        "A2": (94.7, -470.0),
        "A3": (194.7, -470.0),
        "A4": (294.7, -470.0),
        "B1": (-5.3, -320.0),
        "B2": (94.7, -320.0),
        "B3": (194.7, -320.0),
        "B4": (294.7, -320.0),
        "C1": (-5.3, -170.0),
        "C2": (94.7, -170.0),
        "C3": (194.7, -170.0),
        "C4": (294.7, -170.0),
        "D1": (-5.3, -20.0),
        "D2": (94.7, -20.0),
        "D3": (194.7, -20.0),
        "D4": (294.7, -20.0),
    }

    actual = {
        slot: (origin.x, origin.y)
        for slot, origin in PipQuBotXL.SLOT_ORIGINS.items()
    }

    assert actual == expected
