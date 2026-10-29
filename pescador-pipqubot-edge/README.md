# Pescador PipQuBot edge

The existing `main.py` service uses `Pipette` from the adjacent `driver.py`.
The gantry-only `Pescador` variant is preserved beside it in `pescador.py`;
no second service is started. From this folder:

```python
from driver import Pipette
from pescador import Pescador
```

See the repository README for environment, Docker, and baremetal setup.
Imports do not connect to hardware. Starting the service can home and initialize
the pipette. The preserved legacy `Pipette` constructor still omits the explicit
`RLineModel` required by `SatoriusController`; identify the installed head and
configure its model before deployment. No model is guessed by this refactor.

`examples/pipette.py` is a manual hardware-motion script, not an offline test.
