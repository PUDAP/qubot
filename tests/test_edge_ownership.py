"""Offline regression checks for flat machine ownership and safe imports."""

import ast
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OWNERS = [
    ("first-edge", "_first_edge_driver", "driver.py", "First"),
    ("capper-edge", "_capper_edge_driver", "driver.py", "Capper"),
    ("miniqubot-edge", "_miniqubot_edge_driver", "driver.py", "MiniQubot"),
    ("pescador-pipqubot-edge", "_pescador_edge_driver", "driver.py", "Pipette"),
    ("pescador-pipqubot-edge", "_pescador_edge_variant", "pescador.py", "Pescador"),
    ("pipqubot-mof-edge", "_pipqubot_mof_edge_driver", "driver.py", "PipQuBotMOF"),
    ("pipqubot-xl-edge", "_pipqubot_xl_edge_driver", "driver.py", "PipQuBotXL"),
    ("syringequbot-edge", "_syringequbot_edge_driver", "driver.py", "SyringeQubot"),
    ("pipqubot-v3-edge", "_pipqubot_v3_edge_driver", "driver.py", "PipQuBotV3"),
]


@pytest.mark.parametrize("folder,alias,filename,class_name", OWNERS)
def test_machine_is_defined_in_owning_edge(folder, alias, filename, class_name):
    module = importlib.import_module(alias)
    cls = getattr(module, class_name)
    assert module.__file__ is not None
    assert Path(module.__file__).resolve() == ROOT / folder / filename
    assert cls.__module__ == alias
    assert not list((ROOT / folder).glob("qubot_*_edge"))


def test_shared_library_has_no_machine_implementations_or_edge_imports():
    shared = ROOT / "driver" / "src" / "qubot_drivers"
    assert not list((shared / "machines").glob("*.py"))
    aliases = {alias for _, alias, _, _ in OWNERS}
    for path in shared.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                name = module.split(".")[0]
                assert name not in aliases | {"driver", "pescador"}
                assert not (name.startswith("qubot_") and name.endswith("_edge"))


@pytest.mark.parametrize("folder", sorted({owner[0] for owner in OWNERS}))
def test_fresh_edge_and_entrypoint_imports_do_not_touch_hardware(folder):
    # A fresh interpreter per edge exercises real adjacent-file imports, with no
    # installed edge packages, test aliases or ambiguous global driver binding.
    code = '''
import importlib
import importlib.util
import socket
import urllib.request
from pathlib import Path
from unittest.mock import patch
import serial
import websocket

def forbidden(*args, **kwargs):
    raise AssertionError("Import attempted hardware/network access")

with patch.object(serial, "Serial", forbidden), \\
     patch.object(socket.socket, "connect", forbidden), \\
     patch.object(socket.socket, "connect_ex", forbidden), \\
     patch.object(urllib.request, "urlopen", forbidden), \\
     patch.object(websocket, "create_connection", forbidden):
    driver = importlib.import_module("driver")
    assert Path(driver.__file__).resolve() == Path.cwd() / "driver.py"
    if Path("pescador.py").exists():
        assert importlib.import_module("pescador").Pescador
    if Path("main.py").exists():
        importlib.import_module("main")
    assert importlib.util.find_spec("qubot_drivers.machines") is None
    print("Safe adjacent driver/entrypoint imports")
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT / folder,
        env={**os.environ, "PYTHONPATH": str(ROOT / "driver" / "src")},
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Safe adjacent driver/entrypoint imports" in result.stdout


@pytest.mark.parametrize("folder", sorted({owner[0] for owner in OWNERS} - {"pipqubot-v3-edge"}))
def test_entrypoint_imports_adjacent_driver(folder):
    tree = ast.parse((ROOT / folder / "main.py").read_text())
    assert any(isinstance(node, ast.ImportFrom) and node.module == "driver" for node in ast.walk(tree))
