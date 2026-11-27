"""grblHAL NETCON telnet. Same motion calls as the serial controller."""

import socket
import threading
import time
from queue import Empty, Queue
from typing import Optional

from .grbl import GrblHALController

_CONNECTION_CLOSED = "\0GRBL_TELNET_CONNECTION_CLOSED\0"
_REALTIME = {"?", "!", "~"}


def telnet_payload(command: str) -> bytes:
    """Realtime bytes stay raw. Other lines use the NETCON line feed."""
    if command in _REALTIME:
        return command.encode("ascii")
    return (command.rstrip("\r\n") + "\n").encode("ascii")


class GrblTelnetController(GrblHALController):
    """One TCP session to a grblHAL controller. Port 23 is the historical NETCON port."""

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout: float = 30.0,
        feed: int = GrblHALController.DEFAULT_FEEDRATE,
        z_motion: str = "safe_height",
    ):
        super().__init__(port_name=host, timeout=int(timeout), feed=feed, z_motion=z_motion)
        self.host, self.port = _parse_address(host, port)
        self._timeout = float(timeout)
        self._telnet_connected = False
        self._socket: Optional[socket.socket] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._response_queue: Queue[str] = Queue()
        self._transition_lock = threading.Lock()

    def connect(self) -> None:
        """Open NETCON. This does not home."""
        with self._transition_lock:
            if self._telnet_connected:
                return
            self._close_telnet()
            sock = socket.create_connection((self.host, self.port), timeout=self._timeout)
            sock.settimeout(0.2)
            stop_event = threading.Event()
            response_queue: Queue[str] = Queue()
            reader = threading.Thread(
                target=self._read_loop,
                args=(sock, response_queue, stop_event),
                daemon=True,
                name="grbl-telnet",
            )
            self._socket = sock
            self._stop_event = stop_event
            self._response_queue = response_queue
            self._reader_thread = reader
            self._telnet_connected = True
            reader.start()
            self._logger.info("Telnet connected to %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        with self._transition_lock:
            self._close_telnet()

    @property
    def is_connected(self) -> bool:
        return self._telnet_connected

    def execute(self, command: str, value: Optional[str] = None, timeout: Optional[float] = None) -> str:
        """Send one line and return the reply through ``ok``, or one status report for ``?``."""
        del value
        if command == "?":
            return self._query_status(timeout)
        with self._lock:
            queue = self._response_queue
            _drain(queue)
            self._send_line(command)
            return self._read_ok(queue, timeout)

    def halt(self) -> None:
        """Feed-hold with realtime `!`. Does not take the command lock or append LF."""
        sock = self._socket
        if sock is None or not self._telnet_connected:
            raise RuntimeError(
                "GRBL telnet is not open. The controller may still be moving."
            )
        try:
            sock.sendall(telnet_payload("!"))
        except OSError as exc:
            raise RuntimeError(
                "GRBL telnet feed-hold failed. The controller may still be moving."
            ) from exc

    def send_immediate(self, command: str) -> None:
        """Write one NETCON line without the command lock and without waiting for ``ok``."""
        sock = self._socket
        if sock is None or not self._telnet_connected:
            raise RuntimeError(
                "GRBL telnet is not open. The controller may still be moving."
            )
        try:
            sock.sendall(telnet_payload(command))
        except OSError as exc:
            raise RuntimeError(
                "GRBL telnet immediate write failed. The controller may still be moving."
            ) from exc

    def _close_telnet(self) -> None:
        sock = self._socket
        reader = self._reader_thread
        self._stop_event.set()
        self._response_queue.put(_CONNECTION_CLOSED)
        self._socket = None
        self._reader_thread = None
        self._telnet_connected = False
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        if reader is not None and reader is not threading.current_thread() and reader.is_alive():
            reader.join(timeout=1)

    def _read_loop(self, sock: socket.socket, response_queue: Queue[str], stop_event: threading.Event) -> None:
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
                    line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
                    if line:
                        response_queue.put(line)
        finally:
            try:
                sock.close()
            except OSError:
                pass
            response_queue.put(_CONNECTION_CLOSED)
            if self._socket is sock:
                self._socket = None
                self._reader_thread = None
                self._telnet_connected = False

    def _send_line(self, command: str) -> None:
        sock = self._socket
        if sock is None or not self._telnet_connected:
            raise ConnectionError("GRBL telnet is not connected. Call connect() first.")
        try:
            sock.sendall(telnet_payload(command))
        except OSError as exc:
            raise ConnectionError("GRBL telnet connection closed") from exc

    def _query_status(self, timeout: Optional[float]) -> str:
        with self._lock:
            queue = self._response_queue
            _drain(queue)
            self._send_line("?")
            deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                try:
                    message = _next_item(queue, min(0.1, remaining))
                except Empty:
                    continue
                if message.startswith("<"):
                    return message
            raise TimeoutError("Timeout waiting for GRBL status report")

    def _read_ok(self, response_queue: Queue[str], timeout: Optional[float]) -> str:
        """Return every line through the terminal ``ok`` or ``error:``.

        Serial ``execute`` keeps the payload before ``ok`` (``$I``, ``$$``).
        ``ALARM:`` still raises.
        """
        deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
        lines: list[str] = []
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                line = _next_item(response_queue, min(0.1, remaining))
            except Empty:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("ALARM:"):
                raise RuntimeError(f"GRBL command failed: {stripped}")
            lines.append(stripped)
            if stripped == "ok" or stripped.startswith("error:"):
                return "\n".join(lines)
        raise TimeoutError("Timeout waiting for GRBL response")


def _parse_address(host: str, port: int) -> tuple[str, int]:
    address = host.strip().rstrip("/")
    for prefix in ("telnet://", "ws://", "http://", "https://"):
        if address.startswith(prefix):
            address = address[len(prefix):]
            break
    if address.count(":") == 1 and not address.startswith("["):
        parsed_host, embedded = address.rsplit(":", 1)
        return parsed_host, int(embedded)
    return address, port


def _drain(response_queue: Queue[str]) -> None:
    while True:
        try:
            response_queue.get_nowait()
        except Empty:
            return


def _next_item(response_queue: Queue[str], timeout: float) -> str:
    item = response_queue.get(timeout=max(0.0, timeout))
    if item == _CONNECTION_CLOSED:
        raise ConnectionError("GRBL telnet connection closed")
    return item
