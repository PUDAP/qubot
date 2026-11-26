"""Every machine example in docs/examples imports and builds its hardware without a port."""

import importlib.util
from pathlib import Path

import pytest

from qubot.gantry import Frame

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "docs" / "examples").glob("*.py"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"example_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_there_is_one_example_per_known_machine():
    assert [path.stem for path in EXAMPLES] == [
        "claw_machine",
        "dancefloor",
        "eis_qubot",
        "miniqubot",
        "overkill2",
        "photoreactor",
        "pipqubot_mof",
        "pipqubot_xl",
        "syringequbot",
    ]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_builds(path, monkeypatch):
    for index in range(1, 5):
        monkeypatch.setenv(f"FINGER_{index}_PORT", "/dev/null")
    example = _load(path)
    assert isinstance(example.FRAME, Frame)
    example.FRAME.check_limits(example.SOFT_LIMITS)
    assert example.COMMANDS
    assert callable(example.connect_gantry)
    if hasattr(example, "make_chamber"):
        chamber = example.make_chamber()
        with pytest.raises(RuntimeError):
            chamber.loading_position(example.FRAME.hardware_limits["X"])
    if hasattr(example, "make_fingers"):
        assert len(example.make_fingers().fingers) == 4
    if hasattr(example, "Z_LIMITS"):
        assert example.Z_LIMITS == (-125.0, 0.0)
