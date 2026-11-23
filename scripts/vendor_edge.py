"""Copy the packages named by a contract into a site edge's vendor directory.

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


def package_name(path: Path) -> str:
    data = tomllib.loads((path / "pyproject.toml").read_text())
    return data["project"]["name"]


def selected_packages(contract: dict) -> list[tuple[str, Path]]:
    chosen: list[tuple[str, Path]] = []
    gantry_name = str(contract["gantry"])
    gantry = ROOT / "gantries" / gantry_name
    if not gantry.is_dir():
        raise SystemExit(f"missing gantry {gantry_name}")
    chosen.append((f"vendor/gantries/{gantry_name}", gantry))
    effectors = contract.get("effectors", [])
    if not isinstance(effectors, list):
        raise SystemExit("effectors must be a list")
    for effector in effectors:
        directory = ROOT / "end-effectors" / str(effector)
        if not directory.is_dir():
            raise SystemExit(f"missing effector {effector}")
        chosen.append((f"vendor/end-effectors/{effector}", directory))
    for name in ("qubot-geometry", "qubot-edgekit"):
        directory = ROOT / "packages" / name
        if not directory.is_dir():
            raise SystemExit(f"missing package {name}")
        chosen.append((f"vendor/packages/{name}", directory))
    return chosen


def revision() -> tuple[str, str, bool]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subject = subprocess.check_output(["git", "log", "-1", "--format=%s"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    return commit, subject, bool(status.strip())


def write_revision(vendor: Path, copies: list[str]) -> None:
    commit, subject, dirty = revision()
    lines = [
        f"commit={commit}",
        f"subject={subject}",
        f"dirty={'yes' if dirty else 'no'}",
        "packages:",
        *[f"  {item}" for item in copies],
        "",
    ]
    (vendor / "REVISION").write_text("\n".join(lines))


def workspace_block(members: list[tuple[str, str]]) -> str:
    member_lines = "\n".join(f'    "{path}",' for _, path in members)
    source_lines = "\n".join(f"{name} = {{ workspace = true }}" for name, _ in members)
    return (
        f"{MARKER_START}\n"
        "[tool.uv.workspace]\n"
        "members = [\n"
        f"{member_lines}\n"
        "]\n"
        "\n"
        "[tool.uv.sources]\n"
        f"{source_lines}\n"
        f"{MARKER_END}\n"
    )


def update_pyproject(edge: Path, members: list[tuple[str, str]]) -> None:
    manifest = edge / "pyproject.toml"
    if not manifest.is_file():
        raise SystemExit(f"{edge} has no pyproject.toml; scaffold the edge before vendoring")
    block = workspace_block(members)
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
    packages = selected_packages(contract)
    vendor_dir = edge / "vendor"
    if vendor_dir.exists():
        vendor_dir.relative_to(edge)
        shutil.rmtree(vendor_dir)
    vendor_dir.mkdir()
    members: list[tuple[str, str]] = []
    copies: list[str] = []
    for relative, source in packages:
        destination = edge / relative
        shutil.copytree(source, destination, ignore=_ignore)
        members.append((package_name(destination), relative))
        copies.append(relative)
    write_revision(vendor_dir, copies)
    update_pyproject(edge, members)
    return vendor_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("edge", type=Path, help="Site edge directory")
    args = parser.parse_args()
    destination = vendor(args.contract.resolve(), args.edge)
    print(f"vendored packages into {destination}")


if __name__ == "__main__":
    main()
