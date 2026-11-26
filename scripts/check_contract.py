"""Refuse a contract that is incomplete or outside the frame.

Gantries and end effectors are modules of the ``qubot`` package in ``src/``. Pass one or more filled
contract files. A file at ``<edge>/contracts/<version>.toml`` is also checked
against that edge's ``.env.example``.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# These three imports are stdlib-only, so the check runs without pyserial.
from qubot import end_effector  # noqa: E402
from qubot.end_effector import rline as rline_catalog  # noqa: E402
from qubot.gantry import frames  # noqa: E402


def _locked_model(effector: str) -> str | None:
    """Read SELECTED_MODEL without importing the controller, which needs pyserial."""
    path = ROOT / "src" / "qubot" / "end_effector" / f"{end_effector.module_name(effector)}.py"
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SELECTED_MODEL" for target in node.targets
        ):
            return ast.unparse(node.value)
    return None


def _check_rline_50_1000(label: str, contract: dict, effector: str, errors: list[str]) -> None:
    pipette = rline_catalog
    model = pipette.RLineModel.UL_50_1000
    spec = pipette.RLINE_SPECS[model]
    if (
        model.value != "50-1000"
        or spec.minimum_volume_ul != 50
        or spec.maximum_volume_ul != 1000
    ):
        errors.append(f"{label}: {effector} volume range is not 50-1000 uL")
    if spec.microliters_per_step != 2.5:
        errors.append(f"{label}: {effector} is not 2.5 uL per step")
    if effector != "rline-50-1000-multistep":
        return
    if _locked_model(effector) != "RLineModel.UL_50_1000":
        errors.append(f"{label}: {effector} is not locked to the 50-1000 body")
    body = contract.get("effector", {}).get(effector)
    if not isinstance(body, dict):
        errors.append(f"{label}: {effector} contract block is missing")
        return
    if body.get("model") != "50-1000":
        errors.append(f"{label}: {effector} model is not 50-1000")
    if body.get("minimum_volume_ul") != 50 or body.get("maximum_volume_ul") != 1000:
        errors.append(f"{label}: {effector} contract volume range is not 50-1000 uL")
    if body.get("microliters_per_step") != 2.5:
        errors.append(f"{label}: {effector} contract step size is not 2.5 uL")
    step = body.get("step_resolution")
    if isinstance(step, bool) or not isinstance(step, int) or step < 1:
        errors.append(f"{label}: {effector} step_resolution must be a positive integer")
    response = body.get("response_time_s")
    if isinstance(response, bool) or not isinstance(response, (int, float)) or response <= 0:
        errors.append(f"{label}: {effector} response_time_s must be positive")


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
    if str(gantry_name) not in frames.GANTRIES:
        errors.append(f"{label}: missing gantry {gantry_name}")
        return
    frame = frames.load(str(gantry_name))
    placeholders = frames.placeholders(str(gantry_name))
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
        if str(effector) not in end_effector.EFFECTORS:
            errors.append(f"{label}: missing effector {effector}")
    for effector in effectors:
        if effector in {"rline-50-1000", "rline-50-1000-multistep"}:
            _check_rline_50_1000(label, contract, str(effector), errors)
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
