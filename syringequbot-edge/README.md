# Syringe Qubot edge

PUDA edge for the Qubot gantry with a passive syringe. It uses `RepRapHTTPController` from `qubot-drivers`, the same HTTP connection as the old capper.

The syringe has no actuator. Liquid is drawn by the separate `sf10-peristaltic-pump` edge.

Starting the service connects to the RepRap board and does not home. `safe_move_to` retracts to Z 0 before XY movement.

Commands: `home`, `move_to`, `safe_move_to`, `get_position`, `get_status`, `shutdown`, and `reset`. `home`, `move_to`, `safe_move_to`, and `reset` publish `@safety` with `confirm=True`.
