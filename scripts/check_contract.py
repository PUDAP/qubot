"""Refuse a contract that is incomplete or outside the frame.

The ingredient packages live in this repository. Pass one or more filled
contract files. A file at ``<edge>/contracts/<version>.toml`` is also checked
against that edge's ``.env.example``.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_files(paths: list[Path], errors: list[str]) -> None:
    if not paths:
        errors.append("pass at least one contract file")
        return
    for path in paths:
        if not path.is_file():
            errors.append(f"missing contract {path}")
            continue
        contract = tomllib.loads(path.read_text())
        if path.parent.name == "contracts":
            label = f"{path.parent.parent.name} contract {path.stem}"
            if str(contract.get("version")) != path.stem:
                errors.append(f"{path}: version does not match the file name")
            example = path.parent.parent / ".env.example"
            if not example.is_file():
                errors.append(f"{path}: missing .env.example")
            else:
                text = example.read_text()
                if "192.168." in text or "/dev/serial/by-id" in text:
                    errors.append(f"{example}: contains a deployment address")
        else:
            label = str(path)
            if not str(contract.get("version", "")).strip():
                errors.append(f"{label}: version is empty")
        _check_one(label, contract, errors)


def _check_one(label: str, contract: dict, errors: list[str]) -> None:
    machine_id = str(contract.get("machine_id", "")).strip()
    if not machine_id:
        errors.append(f"{label}: machine_id is empty")
    gantry_name = contract.get("gantry")
    if not gantry_name:
        errors.append(f"{label}: gantry is empty")
        return
    gantry_dir = ROOT / "gantries" / str(gantry_name)
    if not gantry_dir.is_dir():
        errors.append(f"{label}: missing gantry {gantry_name}")
        return
    module_name = "gantry_" + str(gantry_name).split("-")[0]
    frame = load_module(gantry_dir / "src" / module_name / "frame.py", f"{module_name}.frame")
    placeholders = tomllib.loads((gantry_dir / "placeholders.toml").read_text())
    for command in placeholders.get("commands", {}):
        filled = contract.get("commands", {}).get(command)
        if not filled or not str(filled.get("summary", "")).strip():
            errors.append(f"{label}: gantry placeholder {command} is empty")
        elif not isinstance(filled.get("confirm"), bool):
            errors.append(f"{label}: {command} confirm must be a boolean")
    if not isinstance(contract.get("home_on_startup"), bool):
        errors.append(f"{label}: home_on_startup must be a boolean")
    effectors = contract.get("effectors", [])
    if not isinstance(effectors, list):
        errors.append(f"{label}: effectors must be a list")
        effectors = []
    for effector in effectors:
        if not (ROOT / "end-effectors" / str(effector)).is_dir():
            errors.append(f"{label}: missing effector {effector}")
    if "rline-50-1000" in effectors:
        pipette = load_module(
            ROOT / "end-effectors" / "rline-50-1000" / "src" / "rline_50_1000" / "rline.py",
            "rline_catalog",
        )
        if pipette.RLineModel.UL_50_1000.value != "50-1000":
            errors.append(f"{label}: pipette model is not 50-1000")
    limits = dict(frame.HARDWARE_LIMITS)
    if contract.get("soft_limits") not in (None, "none"):
        for axis, bounds in contract["soft_limits"].items():
            low, high = bounds
            hard_low, hard_high = limits[axis]
            if low < hard_low or high > hard_high or low > high:
                errors.append(f"{label}: soft {axis} {bounds} is outside {limits[axis]}")
    if "autosampler-syringe" in effectors:
        try:
            length = float(contract["syringe_length_mm"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: syringe_length_mm is a clearance note and must be a number: {exc}")
        else:
            if length < 0:
                errors.append(f"{label}: syringe_length_mm must be zero or positive")


def main(argv: list[str] | None = None) -> None:
    paths = [Path(item) for item in (argv if argv is not None else sys.argv[1:])]
    errors: list[str] = []
    check_files(paths, errors)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("contracts ok")


if __name__ == "__main__":
    main()
