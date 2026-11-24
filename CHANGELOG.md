# Changelog

Ingredient, geometry, edgekit, and contract-template changes are recorded here. A site edge does not append to this file. `scripts/vendor_edge.py` records the commit it copied in that edge's `vendor/REVISION`.

## 2026-11-24

- `rotating-vacuum-gripper`: claw vacuum cup and yaw servo on the gantry port. Intermediate yaw uses linear interpolation between the three calibrated pulses.
- Gantry `005` homes Z, then X, then Y, and can feed-hold with realtime `!` without taking the command lock. `move_relative` accepts `apply_safe_z`.
- `vacuum-chamber`: dancefloor valve and lid waypoints. Loading X=−118 stays outside gantry `006` until the −119 versus −116 limit is confirmed. Gantry `006` can feed-hold the same way.
- Gantry `007` can feed-hold without taking the command lock. `move_relative` accepts `apply_safe_z`. The PESCador pipette reuses `rline-50-1000`.
- `orion-4ch-led`: four-channel LED line on one 9600 baud port. The reply is not parsed. Gantry `008` can feed-hold without taking the command lock.

## 2026-11-23

`main` keeps gantries, end effectors, transport families, geometry, and the edge kit. Finished edges are not stored on `main`. The previous edge tree remains on `legacy-edges`. A site edge is one directory under that site's `edges/`. [docs/building-an-edge.md](docs/building-an-edge.md) is the build reference.

### Gantries

- `001-1unit-grbl-serial`: Integrated as miniqubot.
- `002-1unit-reprap-http`: Integrated as capper, then syringequbot.
- `003-2unit-grbl-serial`: Integrated as pipqubot-mof.
- `004-4unit-reprap-http`: Integrated as pipqubot-xl.
- `005-8unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Claw machine (Pick-and-place). Size is 2 by 4 units. No previous edge.
- `006-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Dancefloor (Vacuum chamber). No previous edge.
- `007-2unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Overkill2 (Liquid handling - pipette gantry). No previous edge.
- `008-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Photoreactor (UV qubot). No previous edge. X −300 to 300 is flagged for correction. A 1-unit frame may travel at most 300 mm on X, and that range spans 600 mm. The uploaded value is unchanged.
- `009-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: EIS Qubot (Electrochemical station). No previous edge. X −300 to 300 is flagged for correction. A 1-unit frame may travel at most 300 mm on X, and that range spans 600 mm. Z −300 to 300 is the same uploaded figure and is flagged with X. The uploaded values are unchanged.

### End effectors

- `rline-50-1000`: Integrated as pipqubot-mof, then pipqubot-xl.
- `a-axis-capper`: Integrated as pipqubot-xl.
- `autosampler-syringe`: Integrated as syringequbot.
