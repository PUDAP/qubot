"""
WebSocket controller for GRBL-compatible motion systems.

Communicates with devices exposing a GRBL command stream over WebSocket.
"""

import logging
import re
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Dict, Optional, Union

import websocket

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


class GrblWSController:
    """Controller for GRBL devices over WebSocket."""

    POLL_INTERVAL = 0.1
    VALID_AXES = "XYZ"
    COMMAND_TERMINATOR = "\n"
    STATUS_STATE_PATTERN = re.compile(r"<(\w+)")
    MPOS_PATTERN = re.compile(r"MPos:(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)")

    def __init__(self, host: str, port: int = 81, timeout: float = 30.0):
        self._url = self._normalize_url(host, port)
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._connected = False
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._connect_event = threading.Event()
        self._response_queue: Queue[str] = Queue()
        self._last_status = ""
        self._axis_limits: Dict[str, AxisLimits] = {
            "X": AxisLimits(0, 0),
            "Y": AxisLimits(0, 0),
            "Z": AxisLimits(0, 0),
        }

        self._logger.info(
            "GrblWSController initialized with url='%s', timeout=%s",
            self._url,
            timeout,
        )

    @staticmethod
    def _normalize_url(host: str, port: int) -> str:
        host = host.strip().rstrip("/")
        if host.startswith("ws://") or host.startswith("wss://"):
            return host
        if host.startswith("http://"):
            host = host[len("http://") :]
        if host.startswith("https://"):
            host = host[len("https://") :]
        if ":" in host:
            return f"ws://{host}"
        return f"ws://{host}:{port}"

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        self._logger.debug("<- Received: %r", message)
        self._response_queue.put(message)
        if message.startswith("<"):
            self._last_status = message

    def _on_error(self, _ws: websocket.WebSocketApp, error: Exception) -> None:
        self._logger.error("WebSocket error: %s", error)

    def _on_close(
        self,
        _ws: websocket.WebSocketApp,
        close_status_code: Optional[int],
        close_msg: Optional[str],
    ) -> None:
        self._connected = False
        self._logger.info(
            "WebSocket closed (code=%s, msg=%s)", close_status_code, close_msg
        )

    def _on_open(self, _ws: websocket.WebSocketApp) -> None:
        self._connected = True
        self._connect_event.set()
        self._logger.info("WebSocket connected to %s", self._url)

    def connect(self) -> None:
        if self._connected:
            return

        self._connect_event.clear()
        self._ws = websocket.WebSocketApp(
            self._url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        self._ws_thread = threading.Thread(
            target=self._ws.run_forever,
            daemon=True,
            name="grbl-ws",
        )
        self._ws_thread.start()

        if not self._connect_event.wait(timeout=self._timeout):
            raise ConnectionError(f"Failed to connect to {self._url}")

    def disconnect(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None
        if self._ws_thread is not None and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=1.0)
            self._ws_thread = None
        self._connected = False
        self._logger.info("Disconnected from %s", self._url)

    def _drain_responses(self) -> None:
        while True:
            try:
                self._response_queue.get_nowait()
            except Empty:
                return

    def _send(self, command: str) -> None:
        if not self._connected or self._ws is None:
            raise ConnectionError("Device disconnected. Call connect() first.")

        payload = command.rstrip("\n") + self.COMMAND_TERMINATOR
        self._logger.info("-> Sending: %r", payload.rstrip())
        self._ws.send(payload)

    @staticmethod
    def _message_has_command_response(message: str) -> bool:
        """Return True if any line in a websocket frame is an ok/error response."""
        for line in message.splitlines():
            stripped = line.strip()
            if stripped == "ok" or stripped.startswith("error:"):
                return True
        return False

    def _read_response(self, timeout: Optional[float] = None) -> str:
        deadline = time.monotonic() + (timeout or self._timeout)
        responses: list[str] = []

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            try:
                message = self._response_queue.get(timeout=min(self.POLL_INTERVAL, remaining))
            except Empty:
                continue

            responses.append(message)
            if self._message_has_command_response(message):
                return "\n".join(responses)

        raise TimeoutError("Timeout waiting for GRBL response")

    def execute(self, command: str, timeout: Optional[float] = None) -> str:
        with self._lock:
            self._drain_responses()
            self._send(command)
            return self._read_response(timeout=timeout)

    def execute_and_wait(self, command: str, timeout: Optional[float] = None) -> str:
        result = self.execute(command, timeout=timeout)
        self.wait_for_idle(timeout=timeout)
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

    def g0(self, position: Position) -> str:
        self.set_absolute_mode()
        return self.execute_and_wait(self._g0_command(position))

    def wait_for_idle(self, timeout: Optional[float] = None) -> None:
        deadline = time.monotonic() + (timeout or self._timeout)
        while time.monotonic() < deadline:
            status = self._query_status()
            if self._is_idle(status):
                return
            time.sleep(self.POLL_INTERVAL)
        raise TimeoutError("Timeout waiting for GRBL to become idle")

    def _query_status(self) -> str:
        with self._lock:
            self._send("?")
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                try:
                    message = self._response_queue.get(
                        timeout=min(self.POLL_INTERVAL, deadline - time.monotonic())
                    )
                except Empty:
                    continue
                if message.startswith("<"):
                    self._last_status = message
                    return message
        raise TimeoutError("Timeout waiting for GRBL status report")

    @staticmethod
    def _is_idle(status: str) -> bool:
        match = GrblWSController.STATUS_STATE_PATTERN.match(status)
        return match is not None and match.group(1) == "Idle"

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
            command = f"$H{axis}"
            home_target = axis
        else:
            command = "$H"
            home_target = "All"

        self._logger.info("Homing axis/axes: %s", home_target)
        self.execute(command, timeout=90)
        self.wait_for_idle(timeout=90)
        self._logger.info("Homing of %s completed", home_target)

    def _position_from_status(self, status: str) -> Position:
        match = self.MPOS_PATTERN.search(status)
        if not match:
            raise ValueError(f"Failed to parse MPos from status report: {status}")

        return Position(
            x=float(match.group(1)),
            y=float(match.group(2)),
            z=float(match.group(3)),
        )

    def get_position(self) -> Position:
        status = self._query_status()
        position = self._position_from_status(status)
        self._logger.info("Query position complete. Retrieved positions: %s", position)
        return position

    def get_status(self) -> dict:
        status = self._query_status()
        match = self.STATUS_STATE_PATTERN.match(status)
        state = match.group(1) if match else "Unknown"
        result = {"state": state, "report": status}
        try:
            result["position"] = self._position_from_status(status).to_dict()
        except ValueError:
            pass
        return result
