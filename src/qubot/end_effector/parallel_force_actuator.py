"""Wire protocol for parallel force actuators. Calibration is configured by the edge.

Force actuators, one per serial port at 115200 baud. The stream line is:

```text
{target},{speed},{displacement},{end_stop},{value}\r\n
```

Home writes `H 0`, waits until the reported displacement is −1.0 mm, disconnects, reconnects, and writes `H 0` again. A move writes `G {mm} {rpm}` with `rpm = int(speed_mm_s * steps_per_second)`. `steps_per_second` is 6400, the actuator default.

Travel defaults to −30 mm to 0 mm. Correction is `(raw − intercept) / slope` per channel. Force in newtons is `(corrected − baseline) / calibration_factor × 9.81`. The edge passes each channel's `(slope, intercept)` and the sensor's `calibration_factor`::

    fingers = ParallelFingers(ports, corrections=[(a0, b0), ...], calibration_factor=...)

Force-threshold stops are not applied here. No finger stop command is known, so a gantry emergency stop does not stop these actuators.
"""

import threading
import time

import serial

COMMUNICATION = "serial"
BAUD = 115200
LIMITS_MM = (-30.0, 0.0)
HOME_DISPLACEMENT_MM = -1.0
GRAVITY_M_S2 = 9.81
STEPS_PER_SECOND = 6400
MAX_SPEED_MM_S = 0.375
HOME_PULSE_S = 1.0
HOME_SETTLE_S = 2.0
HOME_WAIT_TIMEOUT_S = 120.0
MOVE_WAIT_TIMEOUT_S = 300.0
DISPLACEMENT_TOLERANCE_MM = 0.01


def corrected_counts(raw: float, slope: float, intercept: float) -> float:
    """Apply `(raw - intercept) / slope`."""
    if slope == 0:
        raise ValueError("correction slope is zero")
    return (float(raw) - float(intercept)) / float(slope)


def force_newton(
    raw: float, slope: float, intercept: float, baseline: float, calibration_factor: float
) -> float:
    """Newtons from the channel correction and the sensor calibration factor."""
    if calibration_factor == 0:
        raise ValueError("calibration_factor is zero")
    corrected = corrected_counts(raw, slope, intercept)
    return (corrected - float(baseline)) / float(calibration_factor) * GRAVITY_M_S2


def parse_sample(line: str) -> dict:
    """Parse one actuator stream line.

    Raises:
        ValueError: If the line does not have five fields.
    """
    parts = line.strip().split(",")
    if len(parts) != 5:
        raise ValueError(f"Force sample expected 5 fields, got {line!r}")
    end_stop = parts[3].strip().lower()
    if end_stop in {"1", "true"}:
        stopped = True
    elif end_stop in {"0", "false"}:
        stopped = False
    else:
        raise ValueError(f"Unrecognized end_stop {parts[3]!r}")
    return {
        "target_mm": float(parts[0]),
        "speed": float(parts[1]),
        "displacement_mm": float(parts[2]),
        "end_stop": stopped,
        "raw": int(float(parts[4])),
    }


def rpm_for_speed(speed_mm_s: float, steps_per_second: int = STEPS_PER_SECOND) -> int:
    """Convert mm/s to the integer rpm field. Speed must be positive."""
    if speed_mm_s <= 0:
        raise ValueError(f"speed_mm_s must be positive, got {speed_mm_s}")
    return int(speed_mm_s * steps_per_second)


def move_command(to_mm: float, rpm: int, limits_mm: tuple[float, float] = LIMITS_MM) -> str:
    """Displacement command, including the CR LF the board is written with."""
    low, high = limits_mm
    if to_mm < low or to_mm > high:
        raise ValueError(f"Target {to_mm} mm is outside {tuple(limits_mm)}")
    return f"G {round(float(to_mm), 2)} {int(rpm)}\r\n"


def home_command() -> str:
    return "H 0\r\n"


class Finger:
    """One actuator. The reader stores the latest sample. Force stop is not applied here."""

    def __init__(
        self,
        port_name: str,
        channel: int,
        *,
        slope: float,
        intercept: float,
        calibration_factor: float,
        limits_mm: tuple[float, float] = LIMITS_MM,
    ) -> None:
        if slope == 0:
            raise ValueError(f"Channel {channel} correction slope is zero")
        if calibration_factor == 0:
            raise ValueError("calibration_factor is zero")
        low, high = limits_mm
        if low > high:
            raise ValueError(f"limits_mm {tuple(limits_mm)} has low above high")
        self.port_name = port_name
        self.channel = channel
        self.slope = float(slope)
        self.intercept = float(intercept)
        self.calibration_factor = float(calibration_factor)
        self.limits_mm = (float(low), float(high))
        self.baseline = 0.0
        self._serial: serial.Serial | None = None
        self._latest: dict | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._write_lock = threading.Lock()

    def connect(self) -> None:
        """Open the port and start reading stream lines."""
        self._serial = serial.Serial(self.port_name, baudrate=BAUD, timeout=0.2)
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._read_loop,
            name=f"finger-{self.channel}",
            daemon=True,
        )
        self._thread.start()

    def disconnect(self) -> None:
        """Stop the reader and close the port."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        self._thread = None
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def latest(self) -> dict | None:
        """Most recent sample, or None before the first line."""
        if self._latest is None:
            return None
        return dict(self._latest)

    def write_command(self, command: str) -> None:
        """Write one CR LF command.

        Raises:
            RuntimeError: If the port is not open.
        """
        port = self._serial
        if port is None or not port.is_open:
            raise RuntimeError(
                f"Finger {self.channel} on {self.port_name} is not connected"
            )
        payload = command if command.endswith("\r\n") else command + "\r\n"
        with self._write_lock:
            port.write(payload.encode("ascii"))
            port.flush()

    def home(self) -> dict:
        """Home twice, with a disconnect between the two `H 0` writes.

        Raises:
            RuntimeError: If displacement does not reach −1 mm before the timeout.
        """
        self.write_command(home_command())
        time.sleep(HOME_PULSE_S)
        self._wait_displacement(HOME_DISPLACEMENT_MM, HOME_WAIT_TIMEOUT_S)
        self.disconnect()
        time.sleep(HOME_SETTLE_S)
        self.connect()
        time.sleep(HOME_SETTLE_S)
        self.write_command(home_command())
        time.sleep(HOME_PULSE_S)
        displacement = self._wait_displacement(HOME_DISPLACEMENT_MM, HOME_WAIT_TIMEOUT_S)
        return {"channel": self.channel, "displacement_mm": displacement}

    def move_to(self, to_mm: float, speed_mm_s: float) -> dict:
        """Move to a displacement. Does not stop on force.

        The threshold unit is unresolved, so contact is not detected here.

        Raises:
            ValueError: If the target or speed is outside the actuator range.
            RuntimeError: If the reported displacement does not arrive in time.
        """
        command = move_command(to_mm, rpm_for_speed(speed_mm_s), self.limits_mm)
        self.write_command(command)
        displacement = self._wait_displacement(to_mm, MOVE_WAIT_TIMEOUT_S)
        self.write_command(move_command(displacement, rpm_for_speed(speed_mm_s), self.limits_mm))
        sample = self.latest() or {"channel": self.channel}
        sample["channel"] = self.channel
        sample["displacement_mm"] = displacement
        return sample

    def _read_loop(self) -> None:
        pending = b""
        while not self._stop.is_set():
            port = self._serial
            if port is None:
                return
            try:
                chunk = port.read(1)
            except serial.SerialException:
                return
            if not chunk:
                continue
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    sample = parse_sample(text)
                except ValueError:
                    continue
                sample["force_n"] = force_newton(
                    sample["raw"],
                    self.slope,
                    self.intercept,
                    self.baseline,
                    self.calibration_factor,
                )
                sample["channel"] = self.channel
                self._latest = sample

    def _wait_displacement(self, target_mm: float, timeout_s: float) -> float:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            sample = self.latest()
            if sample is not None and abs(sample["displacement_mm"] - target_mm) <= DISPLACEMENT_TOLERANCE_MM:
                return float(sample["displacement_mm"])
            time.sleep(0.01)
        raise RuntimeError(
            f"Finger {self.channel} on {self.port_name} did not reach "
            f"{target_mm} mm within {timeout_s} s"
        )


class ParallelFingers:
    """Channels 0 upward in port order. One ``(slope, intercept)`` correction per port."""

    def __init__(
        self,
        ports: list[str],
        *,
        corrections: list[tuple[float, float]],
        calibration_factor: float,
        limits_mm: tuple[float, float] = LIMITS_MM,
    ) -> None:
        if not ports:
            raise ValueError("No finger ports")
        if len(corrections) != len(ports):
            raise ValueError(f"Expected {len(ports)} corrections, got {len(corrections)}")
        self.fingers = [
            Finger(
                port,
                channel,
                slope=slope,
                intercept=intercept,
                calibration_factor=calibration_factor,
                limits_mm=limits_mm,
            )
            for channel, (port, (slope, intercept)) in enumerate(zip(ports, corrections))
        ]

    def connect(self) -> None:
        for finger in self.fingers:
            finger.connect()

    def disconnect(self) -> None:
        for finger in self.fingers:
            finger.disconnect()

    def finger(self, channel: int) -> Finger:
        if not 0 <= channel < len(self.fingers):
            raise ValueError(f"Channel {channel} is not one of 0 to {len(self.fingers) - 1}")
        return self.fingers[channel]


__all__ = [
    "BAUD",
    "COMMUNICATION",
    "Finger",
    "HOME_DISPLACEMENT_MM",
    "LIMITS_MM",
    "ParallelFingers",
    "STEPS_PER_SECOND",
    "corrected_counts",
    "force_newton",
    "home_command",
    "move_command",
    "parse_sample",
    "rpm_for_speed",
]
