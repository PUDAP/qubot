import json

import pytest

from qubot.gantry import Frame
from qubot.labware import BUNDLED_DIR, Deck, StandardLabware, find_definition, get_available_labware


def _custom(tmp_path, name="edge_plate", z=12.5):
    definition = {
        "metadata": {"displayName": "Edge plate"},
        "dimensions": {"xDimension": 10, "yDimension": 10, "zDimension": z},
        "ordering": [["A1", "B1"], ["A2", "B2"]],
        "wells": {w: {"x": i, "y": i, "z": 1.0} for i, w in enumerate(["A1", "B1", "A2", "B2"])},
        "insert_depth": 5.0,
    }
    (tmp_path / f"{name}.json").write_text(json.dumps(definition))
    return definition


def test_bundled_labware_loads():
    rack = StandardLabware("opentrons_96_tiprack_300ul")
    assert len(rack.wells) == 96
    assert rack.get_height() == 64.49
    assert rack.get_well_position("a1").x is not None
    assert "opentrons_96_tiprack_300ul" in get_available_labware()


def test_edge_folder_adds_labware(tmp_path):
    _custom(tmp_path)
    plate = StandardLabware("edge_plate", search_paths=[tmp_path])
    assert plate.display_name == "Edge plate"
    assert plate.get_insert_depth() == 5.0
    available = get_available_labware([tmp_path])
    assert available["edge_plate"] == {"rows": ["A", "B"], "cols": ["1", "2"]}
    assert "opentrons_96_tiprack_300ul" in available
    with pytest.raises(FileNotFoundError):
        StandardLabware("edge_plate")


def test_edge_definition_overrides_a_bundled_name(tmp_path):
    _custom(tmp_path, name="opentrons_96_tiprack_300ul", z=1.0)
    assert StandardLabware("opentrons_96_tiprack_300ul", search_paths=[tmp_path]).get_height() == 1.0
    assert find_definition("opentrons_96_tiprack_300ul", [tmp_path]).parent == tmp_path
    assert find_definition("opentrons_96_tiprack_300ul").parent == BUNDLED_DIR


def test_from_definition_and_from_file(tmp_path):
    definition = _custom(tmp_path)
    assert StandardLabware.from_definition("inline", definition).wells == ["A1", "B1", "A2", "B2"]
    assert StandardLabware.from_file(tmp_path / "edge_plate.json").name == "edge_plate"


def test_subclass_finds_definitions_next_to_its_module(tmp_path, monkeypatch):
    import inspect

    _custom(tmp_path, name="beside_module")

    class EdgeLabware(StandardLabware):
        pass

    monkeypatch.setattr(inspect, "getfile", lambda obj: str(tmp_path / "edge_labware.py"))
    assert EdgeLabware("beside_module").display_name == "Edge plate"


def test_missing_well_raises():
    rack = StandardLabware("opentrons_96_tiprack_300ul")
    with pytest.raises(KeyError):
        rack.get_well_position("Z99")
    with pytest.raises(KeyError):
        rack.get_height("Z99")


def test_deck_from_frame_loads_edge_and_bundled_labware(tmp_path):
    _custom(tmp_path)
    frame = Frame(axes=("X", "Y", "Z"), hardware_limits={"X": (0, 1), "Y": (0, 1), "Z": (0, 1)},
                  default_deck={"rows": 2, "cols": 2})
    deck = Deck.from_frame(frame, labware_paths=[tmp_path])
    assert list(deck.slots) == frame.slot_names() == ["A1", "A2", "B1", "B2"]
    deck.load_labware("a1", "edge_plate")
    deck.load_labware("B2", "opentrons_96_tiprack_300ul")
    deck.load_labware("A2", StandardLabware.from_definition("inline", _custom(tmp_path, "x")))
    assert deck.to_dict() == {"A1": "edge_plate", "A2": "inline", "B1": None, "B2": "opentrons_96_tiprack_300ul"}
    deck.empty_slot("A1")
    assert deck["a1"] is None
    with pytest.raises(KeyError):
        deck.load_labware("C9", "edge_plate")
