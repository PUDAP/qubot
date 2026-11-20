from _pipqubot_xl_edge_driver import PipQuBotXL


def test_pipqubot_xl_slot_origins_match_calibrated_positions() -> None:
    expected = {
        "A1": (4.3, -470.3),
        "A2": (104.3, -470.3),
        "A3": (204.3, -470.3),
        "A4": (304.3, -470.3),
        "B1": (4.3, -320.3),
        "B2": (104.3, -320.3),
        "B3": (204.3, -320.3),
        "B4": (304.3, -320.3),
        "C1": (4.3, -170.3),
        "C2": (104.3, -170.3),
        "C3": (204.3, -170.3),
        "C4": (304.3, -170.3),
        "D1": (4.3, -20.3),
        "D2": (104.3, -20.3),
        "D3": (204.3, -20.3),
        "D4": (304.3, -20.3),
    }

    actual = {
        slot: (origin.x, origin.y)
        for slot, origin in PipQuBotXL.SLOT_ORIGINS.items()
    }

    assert actual == expected
