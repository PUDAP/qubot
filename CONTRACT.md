# Contract

Read the puda-edge skill and scaffold from
https://github.com/PUDAP/edge-python-template
only after every answer below is filled.
This repository stores the blank form. Start from the matching reference contract in
`docs/examples/<machine>.toml`; it carries `[frame]` and `[effector.<name>]` values
from the machines built so far. The filled contract is saved with the
site edge, under that edge's `contracts/<version>.toml`.
`.env.example` stays placeholders. This repository never stores a host `.env`.
If the user supplies this host's `.env` when asking for a build, copy it into
the site edge with `scripts/accept_host_env.py <edge-directory> <path>`.
Otherwise leave `.env` absent. The edge refuses to start until that file is filled.
Keep the existing edge directory name and `MACHINE_ID`.
Check the filled file with `scripts/check_contract.py <contract.toml>`.
Copy the qubot package into the site edge with
`scripts/vendor_edge.py <contract.toml> <edge-directory>`.
Put that edge directory in the site monorepo's `edges/`. Do not put it in this repository.

Gantry label ({serial}-{size}-{bus}) and qubot revision:
Frame [frame]: axes, hardware_limits, default_deck, home_order, firmware identity and settings:
Effectors:
For each effector [effector.<name>]: axis, port env name, calibration:
Commands [commands.<name>]: safety summary, hazards, requires, forbidden_when, confirm, startup homing:
Soft limits and syringe length, or none:
Deck: gantry default grid, or a replacement. Calibrated slot origins, or uncalibrated:
Advertise deck commands: yes or no
MACHINE_ID:
NATS_SERVERS:
Existing edge this must match:
