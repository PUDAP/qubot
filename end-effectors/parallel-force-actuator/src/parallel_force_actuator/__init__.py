"""Wire protocol and per-channel calibration for the four force actuators."""

import threading
import time

import serial

AXIS = ""
COMMUNICATION = "serial"
PORT_ENVS = ("FINGER_1_PORT", "FINGER_2_PORT", "FINGER_3_PORT", "FINGER_4_PORT")
BAUD = 115200
LIMITS_MM = (-30.0, 0.0)
HOME_DISPLACEMENT_MM = -1.0
CALIBRATION_FACTOR = 573.2622826433104
GRAVITY_M_S2 = 9.81
STEPS_PER_SECOND = 6400
MAX_SPEED_MM_S = 0.375
HOME_PULSE_S = 1.0
HOME_SETTLE_S = 2.0
HOME_WAIT_TIMEOUT_S = 120.0
MOVE_WAIT_TIMEOUT_S = 300.0
DISPLACEMENT_TOLERANCE_MM = 0.01
# pescador2 sets 30000. The demo calls touch with 7500. The library default is 2 * g.
# None of those is applied until the edge contract names the unit.
TOUCH_THRESHOLD_CANDIDATES = (30000, 7500)

CORRECTIONS: dict[int, tuple[float, float]] = {
    0: (1.0453861330027523, -717.008056157306),
    1: (0.8792176759765562, -3546.5827171758337),
    2: (1.0266252637365454, -823.8747617486401),
    3: (0.9109718487428711, -1188.2464990482106),
}


def corrected_counts(raw: float, slope: float, intercept: float) -> float:
    """Apply `(raw - intercept) / slope`."""
    if slope == 0:
        raise ValueError("correction slope is zero")
    return (float(raw) - float(intercept)) / float(slope)


def force_newton(raw: float, slope: float, intercept: float, baseline: float) -> float:
    """Newtons from the written calibration. The threshold unit is still unresolved."""
    corrected = corrected_counts(raw, slope, intercept)
    return (corrected - float(baseline)) / CALIBRATION_FACTOR * GRAVITY_M_S2


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


def move_command(to_mm: float, rpm: int) -> str:
    """Displacement command, including the CR LF the board is written with."""
    low, high = LIMITS_MM
    if to_mm < low or to_mm > high:
        raise ValueError(f"Target {to_mm} mm is outside {LIMITS_MM}")
    return f"G {round(float(to_mm), 2)} {int(rpm)}\r\n"


def home_command() -> str:
    return "H 0\r\n"


class Finger:
    """One actuator. The reader stores the latest sample. Force stop is not applied here."""

    def __init__(self, port_name: str, channel: int) -> None:
        if channel not in CORRECTIONS:
            raise ValueError(f"Channel {channel} is not one of {tuple(CORRECTIONS)}")
        self.port_name = port_name
        self.channel = channel
        self.slope, self.intercept = CORRECTIONS[channel]
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
        command = move_command(to_mm, rpm_for_speed(speed_mm_s))
        self.write_command(command)
        displacement = self._wait_displacement(to_mm, MOVE_WAIT_TIMEOUT_S)
        self.write_command(move_command(displacement, rpm_for_speed(speed_mm_s)))
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
    """Channels 0–3 in port order."""

    def __init__(self, ports: list[str]) -> None:
        if len(ports) != 4:
            raise ValueError(f"Expected 4 finger ports, got {len(ports)}")
        self.fingers = [Finger(port, channel) for channel, port in enumerate(ports)]

    def connect(self) -> None:
        for finger in self.fingers:
            finger.connect()

    def disconnect(self) -> None:
        for finger in self.fingers:
            finger.disconnect()

    def finger(self, channel: int) -> Finger:
        if channel not in CORRECTIONS:
            raise ValueError(f"Channel {channel} is not one of 0, 1, 2, 3")
        return self.fingers[channel]


__all__ = [
    "AXIS",
    "BAUD",
    "CALIBRATION_FACTOR",
    "COMMUNICATION",
    "CORRECTIONS",
    "Finger",
    "HOME_DISPLACEMENT_MM",
    "LIMITS_MM",
    "PORT_ENVS",
    "ParallelFingers",
    "STEPS_PER_SECOND",
    "TOUCH_THRESHOLD_CANDIDATES",
    "corrected_counts",
    "force_newton",
    "home_command",
    "move_command",
    "parse_sample",
    "rpm_for_speed",
]
