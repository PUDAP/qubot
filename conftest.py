"""Load edge-local modules under unique aliases for offline cross-edge tests.

Production entrypoints import their adjacent ``driver.py``. Tests must not put
multiple edges on sys.path or leave any one edge bound globally as ``driver``.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDGE_MODULES = {
    "_first_edge_driver": ("first-edge", "driver.py"),
    "_capper_edge_driver": ("capper-edge", "driver.py"),
    "_miniqubot_edge_driver": ("miniqubot-edge", "driver.py"),
    "_pescador_edge_driver": ("pescador-pipqubot-edge", "driver.py"),
    "_pescador_edge_variant": ("pescador-pipqubot-edge", "pescador.py"),
    "_pipqubot_mof_edge_driver": ("pipqubot-mof-edge", "driver.py"),
    "_pipqubot_xl_edge_driver": ("pipqubot-xl-edge", "driver.py"),
    "_syringequbot_edge_driver": ("syringequbot-edge", "driver.py"),
    "_pipqubot_v3_edge_driver": ("pipqubot-v3-edge", "driver.py"),
}

for alias, (folder, filename) in EDGE_MODULES.items():
    spec = importlib.util.spec_from_file_location(alias, ROOT / folder / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
