"""Four-channel LED line protocol.

Four LED channels on one serial port, 9600 baud, timeout 1 s by default. The edge passes the port.

One write sets every channel:

```text
{p0};{p1};{p2};{p3}\n
```

Off is `0;0;0;0\n`. The reply format is not known, so this package writes the line and does not wait for `ok`.
"""

import serial

COMMUNICATION = "serial"
BAUD = 9600
TIMEOUT_S = 1.0
CHANNELS = (0, 1, 2, 3)


def power_line(powers: list[int]) -> str:
    """Build the four-channel power line.

    Raises:
        ValueError: If the channel count is not 4 or a power is negative.
    """
    if len(powers) != 4:
        raise ValueError(f"LED board expects 4 powers, got {len(powers)}")
    rendered: list[str] = []
    for power in powers:
        if isinstance(power, bool) or not isinstance(power, (int, float)):
            raise ValueError(f"LED power must be a number, got {power!r}")
        if int(power) != power or int(power) < 0:
            raise ValueError(f"LED power must be a non-negative integer, got {power}")
        rendered.append(str(int(power)))
    return ";".join(rendered) + "\n"


class LedBoard:
    """Write-only board. The reply format is unresolved, so reads are not required."""

    def __init__(self, port_name: str, *, baud: int = BAUD, timeout_s: float = TIMEOUT_S) -> None:
        self.port_name = port_name
        self.baud = baud
        self.timeout_s = timeout_s
        self._serial: serial.Serial | None = None
        self.powers = [0, 0, 0, 0]

    def connect(self) -> None:
        self._serial = serial.Serial(self.port_name, baudrate=self.baud, timeout=self.timeout_s)

    def disconnect(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def set_powers(self, p0: int, p1: int, p2: int, p3: int) -> str:
        """Write one power line. Powers are raw board units.

        Raises:
            RuntimeError: If the port is not open.
            ValueError: If a power is not a non-negative integer.
        """
        line = power_line([p0, p1, p2, p3])
        port = self._serial
        if port is None or not port.is_open:
            raise RuntimeError(f"LED port {self.port_name} is not connected")
        port.write(line.encode("ascii"))
        port.flush()
        self.powers = [int(p0), int(p1), int(p2), int(p3)]
        return line

    def off(self) -> str:
        """Write zeros to all four channels."""
        return self.set_powers(0, 0, 0, 0)


__all__ = [
    "BAUD",
    "CHANNELS",
    "COMMUNICATION",
    "LedBoard",
    "TIMEOUT_S",
    "power_line",
]
