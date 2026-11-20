"""Keep edge source directories separate from the shared workspace library."""

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDGE_NAMES = {
    "capper", "first", "miniqubot", "pescador", "pipqubot-mof",
    "pipqubot-v3", "pipqubot-xl", "syringequbot",
}


def test_workspace_owns_all_edge_implementations_under_edges_directory():
    workspace = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["uv"]["workspace"]
    assert set(workspace["members"]) == {"driver", *(f"edges/{name}" for name in EDGE_NAMES)}
    assert {path.parent.name for path in (ROOT / "edges").glob("*/driver.py")} == EDGE_NAMES
    assert not list(ROOT.glob("*-edge/driver.py"))