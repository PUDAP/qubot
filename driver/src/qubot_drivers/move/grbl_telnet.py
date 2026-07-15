"""GRBL controller using grblHAL's full-duplex Telnet stream."""

import logging
import socket
import threading
from queue import Empty, Queue
from typing import Dict, Optional

from .grbl_ws import AxisLimits, GrblWSController


class GrblTelnetController(GrblWSController):
    """Control a grblHAL device through its NETCON Telnet port."""

    def __init__(self, host: str, port: int = 23, timeout: float = 30.0):
        host = host.strip().rstrip("/")
        for prefix in ("telnet://", "ws://", "http://", "https://"):
            if host.startswith(prefix):
                host = host[len(prefix) :]
                break
        if ":" in host:
            host, embedded_port = host.rsplit(":", 1)
            port = int(embedded_port)

        self.host = host
        self.port = port
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._connected = False
        self._socket: Optional[socket.socket] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._response_queue: Queue[str] = Queue()
        self._last_status = ""
        self._lock = threading.Lock()
        self._axis_limits: Dict[str, AxisLimits] = {
            "X": AxisLimits(0, 0),
            "Y": AxisLimits(0, 0),
            "Z": AxisLimits(0, 0),
        }

    def connect(self) -> None:
        if self._connected:
            return
        self._socket = socket.create_connection(
            (self.host, self.port), timeout=self._timeout
        )
        self._socket.settimeout(0.2)
        self._stop_event.clear()
        self._connected = True
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True, name="grbl-telnet"
        )
        self._reader_thread.start()
        self._logger.info("Telnet connected to %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        self._connected = False
        self._stop_event.set()
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
            self._socket = None
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1)
            self._reader_thread = None

    def _read_loop(self) -> None:
        buffer = b""
        while not self._stop_event.is_set() and self._socket is not None:
            try:
                chunk = self._socket.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                raw_line, buffer = buffer.split(b"\n", 1)
                line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
                if not line:
                    continue
                self._logger.debug("<- Received: %r", line)
                if line.startswith("<"):
                    self._last_status = line
                self._response_queue.put(line)
        self._connected = False

    def _send(self, command: str) -> None:
        if not self._connected or self._socket is None:
            raise ConnectionError("Device disconnected. Call connect() first.")
        if command == "?":
            payload = b"?"
        else:
            payload = (command.rstrip("\r\n") + "\n").encode()
        self._logger.info("-> Sending: %r", payload)
        self._socket.sendall(payload)

    def _read_response(self, timeout: Optional[float] = None) -> str:
        import time

        deadline = time.monotonic() + (timeout or self._timeout)
        while time.monotonic() < deadline:
            try:
                line = self._response_queue.get(
                    timeout=min(self.POLL_INTERVAL, deadline - time.monotonic())
                )
            except Empty:
                continue
            stripped = line.strip()
            if stripped.startswith("ALARM:"):
                raise RuntimeError(f"GRBL homing failed: {stripped}")
            if stripped == "ok" or stripped.startswith("error:"):
                return stripped
        raise TimeoutError("Timeout waiting for GRBL response")
