"""Every example contract configures qubot without a machine attached."""

import importlib.util
import shutil
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "docs" / "examples").glob("*.toml"))
ENV = {
    "GANTRY_PORT": "/dev/null",
    "GANTRY_HOST": "localhost",
    "SATORIUS_PORT": "/dev/null",
    "LED_PORT": "/dev/null",
    **{f"FINGER_{index}_PORT": "/dev/null" for index in range(1, 5)},
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _filled(text: str) -> str:
    """Fill the blanks a site edge fills, so the example passes check_contract."""
    text = text.replace('machine_id = ""', 'machine_id = "example"')
    text = text.replace('home_on_startup = ""', "home_on_startup = false")
    text = text.replace('summary = ""', 'summary = "example"')
    return text.replace('confirm = ""', "confirm = true")


def test_there_is_one_example_per_known_machine():
    assert len(EXAMPLES) == 9


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_contract_checks_and_builds(path, tmp_path, monkeypatch):
    edge = tmp_path / "edge"
    (edge / "contracts").mkdir(parents=True)
    (edge / ".env.example").write_text("MACHINE_ID=\n")
    contract = edge / "contracts" / "1.toml"
    contract.write_text(_filled(path.read_text()))

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        check = _load(ROOT / "scripts" / "check_contract.py", "check_contract_under_test")
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    errors: list[str] = []
    check.check_files([contract], errors)
    assert errors == []

    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    shutil.copy(ROOT / "docs" / "examples" / "edge_config.py", edge / "edge_config.py")
    parts = _load(edge / "edge_config.py", "edge_config_under_test").build(edge)
    data = tomllib.loads(contract.read_text())
    assert parts["frame"].axes == tuple(data["frame"]["axes"])
    assert parts["gantry"] is not None
