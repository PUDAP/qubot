# Capper edge

The PUDA service entrypoint is `main.py`. The machine implementation lives in
`driver.py`, imported as `from driver import Capper` from this folder.
It uses the shared `RepRapHTTPController` from `qubot-drivers`.

See the repository README for environment, Docker, and baremetal setup.
Starting this edge can home the gantry. `examples/home_capper.py` is a manual
hardware operation and must not be run without operator approval.
