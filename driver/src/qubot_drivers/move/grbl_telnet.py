"""GRBL controller using grblHAL's full-duplex Telnet stream."""

import logging
import socket
import threading
import time
from queue import Empty, Queue
from typing import Dict, Optional

from .grbl_ws import AxisLimits, GrblWSController


_CONNECTION_CLOSED = "\0GRBL_TELNET_CONNECTION_CLOSED\0"


class GrblTelnetController(GrblWSController):
    """Control a grblHAL device through its NETCON Telnet port."""

    def __init__(self, host: str, port: int = 23, timeout: float = 30.0):
        self.host, self.port = self._parse_address(host, port)
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)
        self._connected = False
        self._socket: Optional[socket.socket] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._response_queue: Queue[str] = Queue()
        self._last_status = ""
        self._lock = threading.Lock()
        self._transition_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._axis_limits: Dict[str, AxisLimits] = {
            "X": AxisLimits(0, 0),
            "Y": AxisLimits(0, 0),
            "Z": AxisLimits(0, 0),
        }

    @staticmethod
    def _parse_address(host: str, port: int) -> tuple[str, int]:
        address = host.strip().rstrip("/")
        for prefix in ("telnet://", "ws://", "http://", "https://"):
            if address.startswith(prefix):
                address = address[len(prefix) :]
                break

        if address.startswith("["):
            closing_bracket = address.find("]")
            if closing_bracket < 0:
                raise ValueError(f"Invalid bracketed host: {host}")
            parsed_host = address[1:closing_bracket]
            remainder = address[closing_bracket + 1 :]
            if remainder:
                if not remainder.startswith(":"):
                    raise ValueError(f"Invalid host/port: {host}")
                port = int(remainder[1:])
            return parsed_host, port

        if address.count(":") == 1:
            parsed_host, embedded_port = address.rsplit(":", 1)
            return parsed_host, int(embedded_port)

        return address, port

    def connect(self) -> None:
        with self._transition_lock:
            with self._state_lock:
                if self._connected:
                    return

            self._close_current_connection()
            sock = socket.create_connection(
                (self.host, self.port), timeout=self._timeout
            )
            sock.settimeout(0.2)
            stop_event = threading.Event()
            response_queue: Queue[str] = Queue()
            reader_thread = threading.Thread(
                target=self._read_loop,
                args=(sock, response_queue, stop_event),
                daemon=True,
                name="grbl-telnet",
            )
            with self._state_lock:
                self._socket = sock
                self._stop_event = stop_event
                self._response_queue = response_queue
                self._reader_thread = reader_thread
                self._connected = True
            reader_thread.start()
            self._logger.info("Telnet connected to %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        with self._transition_lock:
            self._close_current_connection()

    def _close_current_connection(self) -> None:
        with self._state_lock:
            sock = self._socket
            reader_thread = self._reader_thread
            stop_event = self._stop_event
            response_queue = self._response_queue
            self._socket = None
            self._reader_thread = None
            self._connected = False

        stop_event.set()
        response_queue.put(_CONNECTION_CLOSED)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        if (
            reader_thread is not None
            and reader_thread is not threading.current_thread()
            and reader_thread.is_alive()
        ):
            reader_thread.join(timeout=1)

    def _read_loop(
        self,
        sock: socket.socket,
        response_queue: Queue[str],
        stop_event: threading.Event,
    ) -> None:
        buffer = b""
        try:
            while not stop_event.is_set():
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)
                    line = raw_line.rstrip(b"\r").decode(
                        "utf-8", errors="replace"
                    )
                    if not line:
                        continue
                    self._logger.debug("<- Received: %r", line)
                    if line.startswith("<"):
                        self._last_status = line
                    response_queue.put(line)
        finally:
            try:
                sock.close()
            except OSError:
                pass
            response_queue.put(_CONNECTION_CLOSED)
            with self._state_lock:
                if self._socket is sock:
                    self._socket = None
                    self._reader_thread = None
                    self._connected = False

    def _send(self, command: str) -> None:
        with self._state_lock:
            sock = self._socket
            connected = self._connected
        if not connected or sock is None:
            raise ConnectionError("Device disconnected. Call connect() first.")
        if command == "?":
            payload = b"?"
        else:
            payload = (command.rstrip("\r\n") + "\n").encode()
        self._logger.info("-> Sending: %r", payload)
        try:
            sock.sendall(payload)
        except OSError as error:
            raise ConnectionError("GRBL Telnet connection closed") from error

    @staticmethod
    def _drain_queue(response_queue: Queue[str]) -> None:
        while True:
            try:
                response_queue.get_nowait()
            except Empty:
                return

    @staticmethod
    def _get_queue_item(
        response_queue: Queue[str], timeout: float
    ) -> str:
        item = response_queue.get(timeout=timeout)
        if item == _CONNECTION_CLOSED:
            raise ConnectionError("GRBL Telnet connection closed")
        return item

    def execute(self, command: str, timeout: Optional[float] = None) -> str:
        with self._lock:
            response_queue = self._response_queue
            self._drain_queue(response_queue)
            self._send(command)
            return self._read_response_from(response_queue, timeout)

    def _read_response(self, timeout: Optional[float] = None) -> str:
        return self._read_response_from(self._response_queue, timeout)

    def _read_response_from(
        self, response_queue: Queue[str], timeout: Optional[float]
    ) -> str:
        deadline = time.monotonic() + (timeout or self._timeout)
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                line = self._get_queue_item(
                    response_queue,
                    max(0.0, min(self.POLL_INTERVAL, remaining)),
                )
            except Empty:
                continue
            stripped = line.strip()
            if stripped.startswith("ALARM:"):
                raise RuntimeError(f"GRBL homing failed: {stripped}")
            if stripped == "ok" or stripped.startswith("error:"):
                return stripped
        raise TimeoutError("Timeout waiting for GRBL response")

    def _query_status(self) -> str:
        with self._lock:
            response_queue = self._response_queue
            self._drain_queue(response_queue)
            self._send("?")
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                try:
                    message = self._get_queue_item(
                        response_queue,
                        max(0.0, min(self.POLL_INTERVAL, remaining)),
                    )
                except Empty:
                    continue
                if message.startswith("<"):
                    self._last_status = message
                    return message
        raise TimeoutError("Timeout waiting for GRBL status report")
