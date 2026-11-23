# Modularization

A qubot is one gantry plus the end effectors mounted on it. That combination changes. The capper frame later carried a syringe, and the capper still has to be buildable again.

This repository stores the hardware that can be mixed. It does not store a finished edge. A site monorepo holds only the edges for that site. Filling `CONTRACT.md` and running `scripts/vendor_edge.py` copies the named packages into the edge. Frame travel stays on the gantry. Soft limits and the active deck stay in the edge, so a local limit does not rewrite the frame.

`families/` is only a copy source for transport code. `packages/qubot-geometry` holds position, deck, and labware. `packages/qubot-edgekit` loads a numbered contract and refuses to start an edge until a filled local `.env` exists. Machine ids and host `.env` files belong to the site edge.

```mermaid
flowchart TB
  subgraph sources [qubot]
    families["families:<br/>transport snapshots, copy source only"]
    geometry["qubot-geometry:<br/>Position, labware definitions"]
    gantry["gantry package:<br/>serial-size-bus, frame limits, default deck"]
    effector["effector package:<br/>kind, axis, port, communication, body config"]
    families --> gantry
    families --> effector
  end
  contract["contract:<br/>human fills placeholders, ports, and calibration"]
  gantry --> contract
  effector --> contract
  geometry --> contract
  subgraph built [site monorepo edges]
    module["edge driver:<br/>composed commands, soft limits, active deck"]
    edge["edge:<br/>directory name, MACHINE_ID, vendored packages, local dotenv"]
    module --> edge
  end
  contract --> module
```

`002-1unit-reprap-http` was the capper. A syringe edge mounts `autosampler-syringe` on that same frame. A later contract can mount the capper again without copying the syringe edge.
