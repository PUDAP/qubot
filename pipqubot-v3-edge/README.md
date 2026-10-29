# Legacy PipQuBot V3

Owns the preserved `PipQuBotV3` implementation in `driver.py`.
This is a distinct GRBL/Sartorius machine with its own deck calibration and axis
limits, not the MOF machine. It previously had no edge entrypoint or deployment
configuration; none is invented by this move. This is a non-package (virtual)
workspace member, **not a configured runnable service**. From this folder:

```python
from driver import PipQuBotV3
```

Importing the module does not initialize hardware. Do not instantiate or deploy
it without confirming the installed hardware: the legacy constructor still omits
the `RLineModel` required by `SatoriusController`. A future deployment needs that
model, reviewed configuration, and an explicitly authorized startup policy.
