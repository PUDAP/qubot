"""Copy the qubot package into a site edge's vendor directory for its contract.

The whole package is copied to ``vendor/qubot``; the contract picks which
gantry and effector modules the edge imports. ``vendor/REVISION`` records both.

Does not build an image, start a container, or copy a host .env.
Do not point it at an edge that is running.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER_START = "# qubot-vendor:start"
MARKER_END = "# qubot-vendor:end"
SKIP_DIRS = {"__pycache__", ".venv", ".pytest_cache", "dist", ".git"}


def _ignore(directory: str, names: list[str]) -> list[str]:
    del directory
    return [name for name in names if name in SKIP_DIRS or name.endswith((".pyc", ".pyo"))]


PACKAGE_FILES = ("pyproject.toml", "README.md", "LICENSE")


def selected_parts(contract: dict) -> list[str]:
    """Contract gantry and effectors, checked against the qubot package registry."""
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from qubot.end_effector import EFFECTORS
    from qubot.gantry.frames import GANTRIES

    gantry_name = str(contract["gantry"])
    if gantry_name not in GANTRIES:
        raise SystemExit(f"missing gantry {gantry_name}")
    parts = [f"gantry {gantry_name} -> qubot.gantry.frames.{GANTRIES[gantry_name]}"]
    effectors = contract.get("effectors", [])
    if not isinstance(effectors, list):
        raise SystemExit("effectors must be a list")
    for effector in effectors:
        if str(effector) not in EFFECTORS:
            raise SystemExit(f"missing effector {effector}")
        parts.append(f"effector {effector} -> qubot.end_effector.{EFFECTORS[str(effector)]}")
    return parts


def copy_package(destination: Path) -> None:
    destination.mkdir(parents=True)
    for name in PACKAGE_FILES:
        shutil.copy2(ROOT / name, destination / name)
    shutil.copytree(ROOT / "src", destination / "src", ignore=_ignore)


def revision() -> tuple[str, str, bool]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subject = subprocess.check_output(["git", "log", "-1", "--format=%s"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    return commit, subject, bool(status.strip())


def write_revision(vendor: Path, parts: list[str]) -> None:
    commit, subject, dirty = revision()
    lines = [
        f"commit={commit}",
        f"subject={subject}",
        f"dirty={'yes' if dirty else 'no'}",
        "package: vendor/qubot",
        "contract:",
        *[f"  {item}" for item in parts],
        "",
    ]
    (vendor / "REVISION").write_text("\n".join(lines))


def sources_block() -> str:
    return (
        f"{MARKER_START}\n"
        "[tool.uv.sources]\n"
        'qubot = { path = "vendor/qubot" }\n'
        f"{MARKER_END}\n"
    )


def update_pyproject(edge: Path) -> None:
    manifest = edge / "pyproject.toml"
    if not manifest.is_file():
        raise SystemExit(f"{edge} has no pyproject.toml; scaffold the edge before vendoring")
    block = sources_block()
    text = manifest.read_text()
    if MARKER_START in text and MARKER_END in text:
        start = text.index(MARKER_START)
        end = text.index(MARKER_END) + len(MARKER_END)
        text = text[:start] + block.rstrip("\n") + text[end:]
        if not text.endswith("\n"):
            text += "\n"
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    manifest.write_text(text)


def vendor(contract_path: Path, edge: Path) -> Path:
    from check_contract import check_files

    errors: list[str] = []
    check_files([contract_path], errors)
    if errors:
        raise SystemExit("\n".join(errors))
    edge = edge.resolve()
    if not edge.is_dir():
        raise SystemExit(f"missing edge directory {edge}")
    contract = tomllib.loads(contract_path.read_text())
    parts = selected_parts(contract)
    vendor_dir = edge / "vendor"
    if vendor_dir.exists():
        vendor_dir.relative_to(edge)
        shutil.rmtree(vendor_dir)
    vendor_dir.mkdir()
    copy_package(vendor_dir / "qubot")
    write_revision(vendor_dir, parts)
    update_pyproject(edge)
    if "qubot" not in tomllib.loads((edge / "pyproject.toml").read_text()).get("project", {}).get(
        "dependencies", []
    ):
        print('add "qubot" to [project].dependencies in the edge pyproject.toml')
    return vendor_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("edge", type=Path, help="Site edge directory")
    args = parser.parse_args()
    destination = vendor(args.contract.resolve(), args.edge)
    print(f"vendored qubot into {destination}")


if __name__ == "__main__":
    main()
