# qubot

One Python package with the gantry and end-effector drivers for building a PUDA qubot edge. It is published as `qubot-drivers` and imported as `qubot`:

```bash
pip install qubot-drivers        # or: uv add qubot-drivers
```

It holds no machine settings: each edge imports the drivers it needs and configures them in its own code. Nothing in this repository is a running edge. Agents start from the [qubot-driver skill](skills/qubot-driver/SKILL.md). The [design](#design) section explains the split. Changes are recorded in [CHANGELOG.md](CHANGELOG.md).

- No `MACHINE_ID`, NATS servers, host addresses, serial-device paths, frame limits, calibration, container config, or `.env`. A site edge's `.env.example` stays placeholders.
- Code lives in `src/qubot/`. One `pyproject.toml` at the root; gantries and end effectors are modules, not separate packages.
- `qubot.gantry.grbl`, `qubot.gantry.grbl_ws`, `qubot.gantry.reprap_http` are the transports, shared by every gantry.
- `qubot.gantry.Frame` holds one machine's axes, hardware limits, default deck, and optional home order and firmware checks. It refuses limits outside the frame.
- `qubot.end_effector.<name>` is one toolhead driver. Calibration (servo pulses, waypoints, delays, force corrections, pipette pacing) is a constructor argument, and bad values raise.
- `qubot.geometry` is the shared position, deck, and labware module. `qubot.edgekit.require_filled_env` refuses to start an edge until a filled local `.env` exists.
- The [qubot-driver skill](skills/qubot-driver/SKILL.md#reference-drivers) has a starting-point `driver.py` for each known machine, with the values from the machines built so far.
- Finished edges are not stored on `main`. For an edge built before the qubot modularization and the monorepo restructuring, use the `legacy-edges` branch.

A qubot edge's `driver.py` imports what it carries and configures it:

```python
from puda import command, safety

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper
from qubot.geometry import Position

FRAME = Frame(axes=("X", "Y", "Z"),
              hardware_limits={"X": (0, 830), "Y": (-280, 0), "Z": (-240, 0)},
              default_deck={"rows": 4, "cols": 8}, home_order=("Z", "X", "Y"))
GRIPPER = RotatingVacuumGripper(axis="C", yaw_pulses=[(0, 14), (-90, 124), (-180, 244)],
                                rotation_min_z_mm=-5, vacuum_on_delay_s=3, vacuum_off_delay_s=3)


class Driver:
    """Claw machine: 8-unit grblHAL pick-and-place gantry with a rotating vacuum gripper."""

    def __init__(self, gantry_port: str) -> None:
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry)

    def estop(self) -> bool:
        self._gantry.halt()
        return True

    @command
    @safety(summary="Collision risk from gantry motion.", hazards=["collision"], confirm=True)
    def move_absolute(self, x: float | None = None, y: float | None = None, z: float | None = None) -> dict:
        """Move to an absolute position in mm."""
        return self._gantry.move_absolute(Position(x=x, y=y, z=z)).to_dict()
```

## Design

A qubot is one gantry plus the end effectors mounted on it, and that combination changes. The syringequbot frame (`002-1unit-reprap-http`) was the capper first; mounting the capper again is an import in that edge's `driver.py`, not a copy of another edge. So qubot stores only drivers that can be mixed, and each edge in the site monorepo picks and configures its own.

```mermaid
flowchart TB
  subgraph sources [qubot]
    transport["qubot.gantry:<br/>grbl, grbl_ws, reprap_http controllers"]
    gantry["qubot.gantry.Frame:<br/>axes, limit checks, deck slots"]
    effector["qubot.end_effector.name:<br/>protocol, takes calibration as arguments"]
    geometry["qubot.geometry:<br/>Position, labware definitions"]
  end
  config["edge driver.py:<br/>Frame and calibration constants, Driver with @command and @safety"]
  transport --> config
  gantry --> config
  effector --> config
  geometry --> config
  subgraph built [site monorepo edges]
    module["edge main.py:<br/>Config with MACHINE_ID, NATS, ports"]
    edge["edge:<br/>directory name, pinned qubot-drivers, local .env"]
    module --> edge
  end
  config --> module
```

## Supported hardware

### Gantry controllers

| Controller | Import | Firmware and link | Used on |
|---|---|---|---|
| `GrblHALController` | `from qubot.gantry.grbl import GrblHALController` | GRBL 1.1 and grblHAL over USB serial. Feed-hold with realtime `!`. | miniqubot, pipqubot-mof, claw-machine, dancefloor, overkill2, photoreactor, eis-qubot |
| `GrblWSController` | `from qubot.gantry.grbl_ws import GrblWSController` | GRBL over WebSocket (`ws://<host>:81`). | grblHAL gantries with a network board |
| `RepRapHTTPController` | `from qubot.gantry.reprap_http import RepRapHTTPController` | RepRapFirmware over HTTP (`rr_gcode`, `rr_status`). Supports `set_pin`. | syringequbot, pipqubot-xl |

Each controller is paired with a `qubot.gantry.Frame` that holds the machine's axes, travel, and deck.

### End effectors

| End effector | Import | What it is | Link | Used on |
|---|---|---|---|---|
| Sartorius rLine 50-1000 µL | `from qubot.end_effector.rline_50_1000 import connect` | Pipette, 2.5 µL/step, six preset speeds. | Serial | pipqubot-mof, pipqubot-xl |
| Sartorius rLine 50-1000 µL, multistep | `from qubot.end_effector.rline_50_1000_multistep import connect` | Same pipette, with any aspirate/dispense speed up to 1120 µL/s made from paced preset moves. | Serial | overkill2 |
| A-axis capper | `from qubot.end_effector.a_axis_capper import Capper` | Capping tool driven by gantry axis A. | Gantry axis | pipqubot-xl |
| Autosampler syringe | `from qubot.end_effector.autosampler_syringe import narrow_z` | Passive syringe; narrows Z travel by its length. Liquid handling is on a separate pump edge. | None | syringequbot |
| Rotating vacuum gripper | `from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper` | Vacuum cup (coolant valve) and yaw servo (spindle PWM). | Gantry GRBL port | claw-machine |
| Vacuum chamber | `from qubot.end_effector.vacuum_chamber import Chamber` | Chamber valve and lid waypoints, with closed/vented interlocks. | Gantry GRBL port | dancefloor |
| Orion 4-channel LED | `from qubot.end_effector.orion_4ch_led import LedBoard` | Four-channel UV LED board, write-only line protocol. | Serial, 9600 baud | photoreactor |
| Parallel force actuators | `from qubot.end_effector.parallel_force_actuator import ParallelFingers` | Linear actuators with force sensing, one port each. | Serial, 115200 baud | eis-qubot |

Lower-level pieces: `qubot.end_effector.satorius` / `satorius_multistep` (`SatoriusController`), `qubot.end_effector.rline` (rLine 5-200, 50-1000, 100-5000 µL spec table), and `qubot.serialcontroller` (`SerialController` base).

## Build a site edge

Follow the [qubot-driver skill](skills/qubot-driver/SKILL.md): answer its edge checklist, scaffold from [edge-python-template](https://github.com/PUDAP/edge-python-template), pin `qubot-drivers` (a release, or `qubot-drivers @ git+https://github.com/PUDAP/qubot@<ref>`), and start `driver.py` from the matching reference driver. The edge lives in the site monorepo's `edges/`, not in this repository. Build only when that machine is allowed to move.

## Offline checks

```bash
uv sync --group dev
uv run pytest
```
