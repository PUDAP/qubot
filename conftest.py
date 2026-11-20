"""Load edge-local modules under unique aliases for offline cross-edge tests.

Production entrypoints import their adjacent ``driver.py``. Tests must not put
multiple edges on sys.path or leave any one edge bound globally as ``driver``.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDGE_MODULES = {
    "_first_edge_driver": ("edges/first", "driver.py"),
    "_capper_edge_driver": ("edges/capper", "driver.py"),
    "_miniqubot_edge_driver": ("edges/miniqubot", "driver.py"),
    "_pescador_edge_driver": ("edges/pescador", "driver.py"),
    "_pescador_edge_variant": ("edges/pescador", "pescador.py"),
    "_pipqubot_mof_edge_driver": ("edges/pipqubot-mof", "driver.py"),
    "_pipqubot_xl_edge_driver": ("edges/pipqubot-xl", "driver.py"),
    "_syringequbot_edge_driver": ("edges/syringequbot", "driver.py"),
    "_pipqubot_v3_edge_driver": ("edges/pipqubot-v3", "driver.py"),
}

for alias, (folder, filename) in EDGE_MODULES.items():
    spec = importlib.util.spec_from_file_location(alias, ROOT / folder / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
