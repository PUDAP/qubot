"""
HTTP controller for RepRapFirmware motion systems.

Communicates with devices exposing the rr_gcode and rr_status HTTP endpoints.
"""

import asyncio
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

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
    """RepRap controller with the serial controller's motion semantics over HTTP."""

    DEFAULT_FEEDRATE = 3000
    MAX_FEEDRATE = 3000
    MAX_Z_FEED_RATE = 1000
    TOLERANCE = 0.01
    SAFE_MOVE_HEIGHT = -5
    POLL_INTERVAL = 0.1
    VALID_AXES = "XYZA"

    def __init__(
        self,
        host: str,
        timeout: float = 30.0,
        feed: int = DEFAULT_FEEDRATE,
        z_feed: int = MAX_Z_FEED_RATE,
    ):
        self.host = host.strip().rstrip("/")
        if self.host.startswith("http://"):
            self.host = self.host[len("http://") :]
        if self.host.startswith("https://"):
            self.host = self.host[len("https://") :]

        self._base_url = f"http://{self.host}"
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._connected = False
        self._current_position = Position(x=0.0, y=0.0, z=0.0, a=0.0)
        self._feed = feed
        self._z_feed = z_feed
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

    @property
    def feed(self) -> int:
        """Get the current feed rate in mm/min."""
        return self._feed

    @feed.setter
    def feed(self, new_feed: int) -> None:
        """Set the movement feed rate while enforcing the controller maximum."""
        if new_feed <= 0:
            error_msg = (
                f"Attempted to set invalid feed rate: {new_feed}. Must be > 0."
            )
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        if new_feed > self.MAX_FEEDRATE:
            self._logger.warning(
                "Requested feed rate (%s) exceeds maximum (%s). "
                "Setting feed rate to maximum: %s.",
                new_feed,
                self.MAX_FEEDRATE,
                self.MAX_FEEDRATE,
            )
            self._feed = self.MAX_FEEDRATE
        else:
            self._feed = new_feed
            self._logger.debug("Feed rate set to: %s mm/min.", self._feed)

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
        self._wait_for_move()
        return result

    def _wait_for_move(self) -> None:
        """Wait for queued HTTP motion commands to finish."""
        self.wait_for_idle()

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

    def _validate_axis(self, axis: str) -> str:
        """Validate and normalize an axis name."""
        axis_upper = axis.upper()
        if axis_upper not in self.VALID_AXES:
            self._logger.error(
                "Invalid axis '%s' provided. Must be one of: %s.",
                axis_upper,
                ", ".join(self.VALID_AXES),
            )
            raise ValueError(
                f"Invalid axis. Must be one of: {', '.join(self.VALID_AXES)}."
            )
        return axis_upper

    def _validate_move_positions(self, position: Position) -> None:
        """Validate all axes present in a target position."""
        for axis in self.VALID_AXES:
            key = axis.lower()
            if not position.has_axis(key):
                continue
            try:
                self._axis_limits[axis].validate(position[key])
            except ValueError as exc:
                self._logger.error(
                    "Move validation failed for %s axis: %s", axis, exc
                )
                raise

    def move_absolute(
        self,
        position: Position,
        feed: Optional[int] = None,
    ) -> Position:
        """Move to an absolute position using the serial controller's safe path."""
        self._validate_move_positions(position)
        feed_rate = feed if feed is not None else self._feed
        self._logger.info(
            "Preparing absolute move to X:%s, Y:%s, Z:%s, A:%s at F:%s",
            position.x,
            position.y,
            position.z,
            position.a,
            feed_rate,
        )
        return self._execute_move(position=position, feed=feed_rate)

    def move_relative(
        self,
        position: Position,
        feed: Optional[int] = None,
    ) -> Position:
        """Apply relative deltas through the same bounded safe-move path."""
        abs_x = self._current_position.x
        abs_y = self._current_position.y
        abs_z = self._current_position.z
        abs_a = self._current_position.a

        if position.has_axis("x"):
            abs_x += position.x
        if position.has_axis("y"):
            abs_y += position.y
        if position.has_axis("z"):
            abs_z += position.z
        if position.has_axis("a"):
            abs_a += position.a

        abs_position = Position(x=abs_x, y=abs_y, z=abs_z, a=abs_a)
        self._validate_move_positions(abs_position)

        feed_rate = feed if feed is not None else self._feed
        self._logger.info(
            "Preparing relative move by dX:%s, dY:%s, dZ:%s, dA:%s at F:%s",
            position.x if position.has_axis("x") else 0,
            position.y if position.has_axis("y") else 0,
            position.z if position.has_axis("z") else 0,
            position.a if position.has_axis("a") else 0,
            feed_rate,
        )
        return self._execute_move(position=abs_position, feed=feed_rate)

    def _execute_move(self, position: Position, feed: int) -> Position:
        """
        Execute an absolute move with the same safe sequence as RepRapController.

        If X or Y changes, Z and A first retract to ``SAFE_MOVE_HEIGHT``.
        Horizontal movement completes next, followed by the requested Z or A
        destination.
        """
        needs_x_move = (
            abs(position.x - self._current_position.x) > self.TOLERANCE
        )
        needs_y_move = (
            abs(position.y - self._current_position.y) > self.TOLERANCE
        )
        needs_z_move = abs(position.z) > self.TOLERANCE
        needs_a_move = abs(position.a) > self.TOLERANCE

        if not (needs_x_move or needs_y_move or needs_z_move or needs_a_move):
            self._logger.warning(
                "Move command issued without any axis movement. "
                "Skipping transmission."
            )
            return

        if needs_z_move and needs_a_move:
            self._logger.error(
                "Move command issued with both Z and A movement. "
                "This is not supported. Skipping transmission."
            )
            raise ValueError(
                "Move command issued with both Z and A movement. "
                "This is not supported."
            )

        self.execute("G90")

        if needs_x_move or needs_y_move:
            self._logger.debug(
                "Safe move: raising Z and A to safe height (%s) before XY movement",
                self.SAFE_MOVE_HEIGHT,
            )
            move_cmd = (
                f"G1 Z{self.SAFE_MOVE_HEIGHT} A{self.SAFE_MOVE_HEIGHT} "
                f"F{self._z_feed}"
            )
            self.execute(move_cmd)
            self._wait_for_move()
            self._current_position.z = self.SAFE_MOVE_HEIGHT
            self._current_position.a = self.SAFE_MOVE_HEIGHT

            needs_z_move = (
                abs(position.z - self._current_position.z) > self.TOLERANCE
            )
            needs_a_move = (
                abs(position.a - self._current_position.a) > self.TOLERANCE
            )

        if needs_x_move or needs_y_move:
            move_cmd = "G1"
            if needs_x_move:
                move_cmd += f" X{position.x}"
            if needs_y_move:
                move_cmd += f" Y{position.y}"
            move_cmd += f" F{feed}"
            self.execute(move_cmd)
            self._wait_for_move()

            if needs_x_move:
                self._current_position.x = position.x
            if needs_y_move:
                self._current_position.y = position.y

        if needs_z_move:
            self.execute(f"G1 Z{position.z} F{self._z_feed}")
            self._wait_for_move()
            self._current_position.z = position.z
        if needs_a_move:
            self.execute(f"G1 A{position.a} F{self._z_feed}")
            self._wait_for_move()
            self._current_position.a = position.a

        self._logger.debug("New internal position: %s", self._current_position)
        return self._current_position

    def set_pin(self, pin: int, state: int) -> dict:
        return self.execute(f"M42 P{pin} S{state}")

    def wait_for_idle(self) -> None:
        while True:
            data = self._get_status()
            if data.get("status") == "I":
                return
            time.sleep(self.POLL_INTERVAL)

    def set_axis_limits(self, axis: str, min_val: float, max_val: float) -> None:
        axis = self._validate_axis(axis)
        if min_val >= max_val:
            raise ValueError("min must be < max")

        self._axis_limits[axis] = AxisLimits(min_val, max_val)
        self._logger.info("Set limits for axis %s: [%s, %s]", axis, min_val, max_val)

    def get_axis_limits(
        self, axis: Optional[str] = None
    ) -> Union[AxisLimits, Dict[str, AxisLimits]]:
        if axis is None:
            return self._axis_limits.copy()

        axis = self._validate_axis(axis)
        return self._axis_limits[axis]

    def home(self, axis: Optional[str] = None) -> None:
        if axis:
            axis = self._validate_axis(axis)
            command = f"G28 {axis}"
            home_target = axis
        else:
            command = "G28"
            home_target = "All"

        self._logger.info("Homing axis/axes: %s", home_target)
        self.execute(command)
        self.wait_for_idle()
        self._logger.info("Homing of %s completed", home_target)

        if axis:
            self._current_position[axis.lower()] = 0.0
        else:
            self._current_position = Position(x=0.0, y=0.0, z=0.0, a=0.0)

        self._logger.debug(
            "Internal position updated (optimistically zeroed) to %s",
            self._current_position,
        )

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

    async def get_position(self) -> Position:
        """Get the current position without blocking the caller's event loop."""
        self._logger.info("Querying current machine position over HTTP.")
        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(self._get_status),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            self._logger.info(
                "HTTP position query timed out after 1 second. "
                "Falling back to internal position."
            )
            return self.get_internal_position()

        position = self._position_from_status(data)
        self._logger.info("Query position complete. Retrieved positions: %s", position)
        return position

    def _sync_position(self) -> Tuple[bool, Position]:
        """Synchronize the tracked position using the HTTP status endpoint."""
        self._logger.info("Starting position synchronization check over HTTP.")
        queried_position = asyncio.run(self.get_position())

        if not queried_position.get_axes():
            self._logger.error("Query position failed. Cannot synchronize.")
            raise ValueError("Query position failed. Cannot synchronize.")

        adjustment_needed = False
        for axis in ("x", "y", "z", "a"):
            if (
                self._current_position.has_axis(axis)
                and queried_position.has_axis(axis)
                and abs(self._current_position[axis] - queried_position[axis])
                > self.TOLERANCE
            ):
                self._logger.warning(
                    "Position mismatch found on %s axis: Internal=%.3f, Queried=%.3f",
                    axis.upper(),
                    self._current_position[axis],
                    queried_position[axis],
                )
                adjustment_needed = True
            elif queried_position.has_axis(axis):
                self._current_position[axis] = queried_position[axis]

        if adjustment_needed:
            self._logger.info(
                "Discrepancy detected. Moving robot to internal position: %s",
                self._current_position,
            )
            try:
                self.move_absolute(position=self._current_position.copy())
                self._logger.info("Synchronization move successfully completed.")
                return self._sync_position()
            except (ValueError, RuntimeError, OSError) as exc:
                self._logger.error("Synchronization move failed: %s", exc)
                adjustment_needed = False

        if adjustment_needed:
            self._logger.info(
                "Position check complete. Internal position is synchronized with machine."
            )
        else:
            self._logger.info("No adjustment was made.")

        return adjustment_needed, self._current_position.copy()

    def get_info(self) -> dict:
        """Query machine information with M115 over HTTP."""
        self._logger.info("Querying machine information (M115).")
        return self.execute("M115")

    def get_internal_position(self) -> Position:
        """Return a copy of the internally tracked position."""
        self._logger.debug("Returning internal position: %s", self._current_position)
        return self._current_position.copy()

    def get_status(self) -> dict:
        return self._get_status()
