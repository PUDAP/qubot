"""
HTTP controller for RepRapFirmware motion systems.

Communicates with devices exposing the rr_gcode and rr_status HTTP endpoints.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Union

from qubot_drivers.position import Position


@dataclass
class AxisLimits:
    """Holds min/max limits for an axis."""

    min: float
    max: float

    def validate(self, value: float) -> None:
        if not (self.min <= value <= self.max):
            raise ValueError(
                f"Value {value} outside axis limits [{self.min}, {self.max}]"
            )


class RepRapHTTPController:
    """Controller for RepRapFirmware devices over HTTP."""

    POLL_INTERVAL = 0.1
    VALID_AXES = "XYZA"

    def __init__(self, host: str, timeout: float = 30.0):
        self.host = host.strip().rstrip("/")
        if self.host.startswith("http://"):
            self.host = self.host[len("http://") :]
        if self.host.startswith("https://"):
            self.host = self.host[len("https://") :]

        self._base_url = f"http://{self.host}"
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._connected = False
        self._axis_limits: Dict[str, AxisLimits] = {
            "X": AxisLimits(0, 0),
            "Y": AxisLimits(0, 0),
            "Z": AxisLimits(0, 0),
            "A": AxisLimits(0, 0),
        }

        self._logger.info(
            "RepRapHTTPController initialized with host='%s', timeout=%s",
            self.host,
            timeout,
        )

    def _request(self, path: str, params: Optional[Dict[str, str]] = None) -> dict:
        url = f"{self._base_url}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as response:
                body = response.read().decode()
        except urllib.error.URLError as exc:
            self._logger.error("HTTP request failed for %s: %s", url, exc)
            raise ConnectionError(f"Failed to reach RepRap device at {self.host}") from exc

        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"response": body}

    def connect(self) -> None:
        self._get_status()
        self._connected = True
        self._logger.info("Connected to RepRap device at %s", self.host)

    def disconnect(self) -> None:
        self._connected = False
        self._logger.info("Disconnected from RepRap device at %s", self.host)

    def _get_status(self) -> dict:
        return self._request("rr_status", {"type": "1"})

    def execute(self, command: str) -> dict:
        return self._request("rr_gcode", {"gcode": command})

    def execute_and_wait(self, command: str) -> dict:
        result = self.execute(command)
        self.wait_for_idle()
        return result

    def set_absolute_mode(self) -> None:
        self.execute("G90")

    def set_relative_mode(self) -> None:
        self.execute("G91")

    def _g0_command(self, position: Position) -> str:
        parts = ["G0"]
        for axis in self.VALID_AXES:
            key = axis.lower()
            if position.has_axis(key):
                parts.append(f"{axis}{position[key]}")
        if len(parts) == 1:
            raise ValueError("At least one axis required for G0 move")
        return "".join(parts)

    def g0(self, position: Position) -> dict:
        return self.execute_and_wait(self._g0_command(position))

    def set_pin(self, pin: int, state: int) -> dict:
        return self.execute(f"M42 P{pin} S{state}")

    def wait_for_idle(self) -> None:
        while True:
            data = self._get_status()
            if data.get("status") == "I":
                return
            time.sleep(self.POLL_INTERVAL)

    def set_axis_limits(self, axis: str, min_val: float, max_val: float) -> None:
        axis = axis.upper()
        if axis not in self.VALID_AXES:
            raise ValueError(
                f"Invalid axis. Must be one of: {', '.join(self.VALID_AXES)}."
            )
        if min_val >= max_val:
            raise ValueError("min must be < max")

        self._axis_limits[axis] = AxisLimits(min_val, max_val)
        self._logger.info("Set limits for axis %s: [%s, %s]", axis, min_val, max_val)

    def get_axis_limits(
        self, axis: Optional[str] = None
    ) -> Union[AxisLimits, Dict[str, AxisLimits]]:
        if axis is None:
            return self._axis_limits.copy()

        axis = axis.upper()
        if axis not in self.VALID_AXES:
            raise ValueError(
                f"Invalid axis. Must be one of: {', '.join(self.VALID_AXES)}."
            )
        return self._axis_limits[axis]

    def home(self, axis: Optional[str] = None) -> None:
        if axis:
            axis = axis.upper()
            if axis not in self.VALID_AXES:
                raise ValueError(
                    f"Invalid axis. Must be one of: {', '.join(self.VALID_AXES)}."
                )
            command = f"G28 {axis}"
            home_target = axis
        else:
            command = "G28"
            home_target = "All"

        self._logger.info("Homing axis/axes: %s", home_target)
        self.execute(command)
        self.wait_for_idle()
        self._logger.info("Homing of %s completed", home_target)

    def _position_from_status(self, data: dict) -> Position:
        coords = data.get("coords", {})
        xyz = coords.get("xyz", [])

        if isinstance(xyz, dict):
            return Position.from_dict({k.lower(): float(v) for k, v in xyz.items()})

        position_data: Dict[str, float] = {}
        axis_names = ["x", "y", "z", "a"]
        for index, value in enumerate(xyz):
            if index >= len(axis_names):
                break
            position_data[axis_names[index]] = float(value)

        abc = coords.get("abc", [])
        if len(abc) > 0 and "a" not in position_data:
            position_data["a"] = float(abc[0])

        return Position.from_dict(position_data)

    def get_position(self) -> Position:
        data = self._get_status()
        position = self._position_from_status(data)
        self._logger.info("Query position complete. Retrieved positions: %s", position)
        return position

    def get_status(self) -> dict:
        return self._get_status()
