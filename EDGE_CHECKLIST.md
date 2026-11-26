# Edge checklist

Answer every item before scaffolding an edge from
https://github.com/PUDAP/edge-python-template (read the puda-edge skill first).
The answers go into the edge's own code, usually a `hardware.py` next to
`driver.py`, which imports qubot and constructs the gantry and end effectors.
Start from the matching machine in [docs/examples/](docs/examples/) if there is one.

Keep the existing edge directory name and `MACHINE_ID`. Put the edge in the site
monorepo's `edges/`, never in this repository. `.env.example` stays placeholders.
If the user supplies this host's `.env`, copy it with
`python3 scripts/accept_host_env.py <edge-directory> <path>`; otherwise leave `.env`
absent, and the edge refuses to start until it is filled (`qubot.edgekit.require_filled_env`).

- qubot version or git ref the edge pins:
- Gantry transport (`GrblHALController`, `GrblWSController`, `RepRapHTTPController`) and its port or host env name:
- `Frame`: axes, hardware limits, default deck, home order, expected firmware identity and settings:
- Soft limits inside the frame, or none:
- Startup homing: yes or no:
- For each command the edge advertises: safety summary, hazards, requires, forbidden_when, confirm:
- End effectors, and for each: axis, port env name, calibration values:
- Syringe length, if an autosampler syringe is mounted:
- Deck: frame default grid, or a replacement. Calibrated slot origins, or uncalibrated:
- Advertise deck commands: yes or no:
- MACHINE_ID:
- NATS_SERVERS:
- Existing edge this must match:
