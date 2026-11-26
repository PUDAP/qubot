"""How a site edge imports qubot and configures it from its own contract.

Copy the parts you need into the edge's driver. Values come from
``<edge>/contracts/<version>.toml``; ports come from the edge's ``.env``.
Nothing here is a running edge.
"""

from __future__ import annotations

import os
from pathlib import Path

from qubot.edgekit import load_contract
from qubot.gantry import Frame

EDGE_DIR = Path(__file__).resolve().parent


def build(edge_dir: Path = EDGE_DIR) -> dict:
    contract = load_contract(edge_dir)
    frame = Frame.from_dict(contract["frame"])
    effectors = contract.get("effectors", [])
    blocks = contract.get("effector", {})
    parts: dict = {"contract": contract, "frame": frame}

    # Gantry transport: pick the one that matches the frame's bus.
    if "reprap-http" in contract["gantry"]:
        from qubot.gantry.reprap_http import RepRapHTTPController

        gantry = RepRapHTTPController(host=os.environ["GANTRY_HOST"])
    else:
        from qubot.gantry.grbl import GrblHALController

        gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    parts["gantry"] = gantry
    # After gantry.connect(): frame.apply_axis_limits(gantry, contract.get("soft_limits"))

    if "rline-50-1000" in effectors:
        from qubot.end_effector.rline_50_1000 import connect

        parts["pipette"] = connect(os.environ["SATORIUS_PORT"])
    if "rline-50-1000-multistep" in effectors:
        from qubot.end_effector.rline_50_1000_multistep import connect

        body = blocks["rline-50-1000-multistep"]
        parts["pipette"] = connect(
            os.environ["SATORIUS_PORT"],
            step_resolution=body["step_resolution"],
            response_time_s=body["response_time_s"],
        )
    if "a-axis-capper" in effectors:
        from qubot.end_effector.a_axis_capper import Capper

        parts["capper"] = Capper(**blocks["a-axis-capper"])
    if "autosampler-syringe" in effectors:
        from qubot.end_effector.autosampler_syringe import narrow_z

        parts["z_limits"] = narrow_z(frame.hardware_limits["Z"], contract["syringe_length_mm"])
    if "rotating-vacuum-gripper" in effectors:
        from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper

        parts["gripper"] = RotatingVacuumGripper(**blocks["rotating-vacuum-gripper"])
    if "vacuum-chamber" in effectors:
        from qubot.end_effector.vacuum_chamber import Chamber

        parts["chamber"] = Chamber(**blocks["vacuum-chamber"])
    if "orion-4ch-led" in effectors:
        from qubot.end_effector.orion_4ch_led import LedBoard

        body = blocks["orion-4ch-led"]
        parts["led"] = LedBoard(os.environ["LED_PORT"], baud=body["baud"], timeout_s=body["timeout_s"])
    if "parallel-force-actuator" in effectors:
        from qubot.end_effector.parallel_force_actuator import ParallelFingers

        body = blocks["parallel-force-actuator"]
        ports = [os.environ[f"FINGER_{index}_PORT"] for index in range(1, len(body["corrections"]) + 1)]
        parts["fingers"] = ParallelFingers(
            ports,
            corrections=[tuple(pair) for pair in body["corrections"]],
            calibration_factor=body["calibration_factor"],
            limits_mm=tuple(body["limits_mm"]),
        )
    return parts
