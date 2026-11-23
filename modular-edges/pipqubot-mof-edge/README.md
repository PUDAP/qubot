# MOF PipQuBot Edge

PUDA edge service for the MOF PipQuBot. It connects the GRBL gantry and Sartorius pipette serial controllers, then publishes machine commands and telemetry through NATS.

Starting this edge runs the machine driver's startup routine, which connects both controllers, homes the gantry, and initializes the pipette.
