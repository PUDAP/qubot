import socket
import threading
import time

import pytest

from qubot_drivers.machines.pescador import Pescador
from qubot_drivers.machines.pipette import Pipette
from qubot_drivers.move.grbl_telnet import GrblTelnetController


class FakeGrblServer:
    def __init__(self, handler):
        self._handler = handler
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.host, self.port = self._server.getsockname()
        self.received = []
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._server.close()
        self._thread.join(timeout=1)

    def _run(self):
        connection, _ = self._server.accept()
        with connection:
            connection.sendall(b"GrblHAL 1.1f\r\n")
            buffer = b""
            while True:
                chunk = connection.recv(1024)
                if not chunk:
                    return
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    command = raw.rstrip(b"\r").decode()
                    self.received.append(command)
                    self._handler(connection, command)
                if buffer == b"?":
                    buffer = b""
                    self.received.append("?")
                    self._handler(connection, "?")


def test_execute_sends_line_and_returns_ok():
    def respond(connection, command):
        if command == "$I":
            connection.sendall(b"[VER:1.1f]\r\nok\r\n")

    with FakeGrblServer(respond) as server:
        controller = GrblTelnetController(server.host, port=server.port, timeout=1)
        controller.connect()
        try:
            response = controller.execute("$I")
        finally:
            controller.disconnect()

    assert server.received == ["$I"]
    assert response == "ok"


def test_status_query_is_sent_as_single_realtime_byte():
    received = []
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(1)
    host, port = server_socket.getsockname()

    def serve():
        connection, _ = server_socket.accept()
        with connection:
            payload = connection.recv(16)
            received.append(payload)
            connection.sendall(
                b"<Idle|MPos:1.000,2.000,3.000|FS:0,0>\r\n"
            )

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    controller = GrblTelnetController(host, port=port, timeout=1)
    controller.connect()
    try:
        status = controller._query_status()
    finally:
        controller.disconnect()
        server_socket.close()
        thread.join(timeout=1)

    assert received == [b"?"]
    assert status.startswith("<Idle|")


def test_alarm_raises_immediately_instead_of_timing_out():
    def respond(connection, command):
        if command == "$H":
            connection.sendall(b"ALARM:9\r\n")

    with FakeGrblServer(respond) as server:
        controller = GrblTelnetController(server.host, port=server.port, timeout=0.2)
        controller.connect()
        try:
            with pytest.raises(RuntimeError, match="ALARM:9"):
                controller.execute("$H")
        finally:
            controller.disconnect()


def test_pescador_machines_use_telnet_motion_controller():
    pipette = Pipette(qubot_ip="192.0.2.1", satorius_port="/dev/null")
    pescador = Pescador(qubot_ip="192.0.2.1")

    assert isinstance(pipette.qubot, GrblTelnetController)
    assert isinstance(pescador.qubot, GrblTelnetController)


def test_home_waits_for_acknowledgement_then_idle_status():
    def respond(connection, command):
        if command == "$H":
            connection.sendall(b"<Home|MPos:0,0,0>\r\n")
            connection.sendall(b"ok\r\n")
        elif command == "?":
            connection.sendall(b"<Idle|MPos:0,0,0|FS:0,0>\r\n")

    with FakeGrblServer(respond) as server:
        controller = GrblTelnetController(server.host, port=server.port, timeout=1)
        controller.connect()
        try:
            controller.home()
        finally:
            controller.disconnect()

    assert server.received == ["$H", "?"]


def test_connect_discards_status_from_previous_connection():
    def respond(connection, command):
        if command == "?":
            connection.sendall(b"<Idle|MPos:4,5,6|FS:0,0>\r\n")

    with FakeGrblServer(respond) as server:
        controller = GrblTelnetController(server.host, port=server.port, timeout=1)
        controller._response_queue.put("<Alarm|MPos:1,2,3>")
        controller.connect()
        try:
            status = controller._query_status()
        finally:
            controller.disconnect()

    assert status == "<Idle|MPos:4,5,6|FS:0,0>"


def test_peer_eof_interrupts_execute_without_waiting_for_timeout():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(1)
    host, port = server_socket.getsockname()

    def serve():
        connection, _ = server_socket.accept()
        with connection:
            connection.recv(16)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    controller = GrblTelnetController(host, port=port, timeout=2)
    controller.connect()
    started = time.monotonic()
    try:
        with pytest.raises(ConnectionError, match="connection closed"):
            controller.execute("$I")
    finally:
        controller.disconnect()
        server_socket.close()
        thread.join(timeout=1)

    assert time.monotonic() - started < 1


def test_disconnect_interrupts_inflight_execute():
    command_received = threading.Event()

    def respond(_connection, command):
        if command == "$H":
            command_received.set()

    with FakeGrblServer(respond) as server:
        controller = GrblTelnetController(server.host, port=server.port, timeout=2)
        controller.connect()
        result = []

        def execute():
            try:
                controller.execute("$H")
            except Exception as error:
                result.append(error)

        thread = threading.Thread(target=execute)
        thread.start()
        assert command_received.wait(timeout=1)
        controller.disconnect()
        thread.join(timeout=1)

    assert not thread.is_alive()
    assert len(result) == 1
    assert isinstance(result[0], ConnectionError)


@pytest.mark.parametrize(
    ("address", "expected_host", "expected_port"),
    [
        ("::1", "::1", 23),
        ("[2001:db8::1]", "2001:db8::1", 23),
        ("[2001:db8::1]:2323", "2001:db8::1", 2323),
    ],
)
def test_ipv6_hosts_are_parsed_without_confusing_address_for_port(
    address, expected_host, expected_port
):
    controller = GrblTelnetController(address)

    assert controller.host == expected_host
    assert controller.port == expected_port


def test_reconnect_after_peer_eof_uses_a_fresh_socket_and_queue():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(2)
    host, port = server_socket.getsockname()
    accepted = []

    def serve():
        first, _ = server_socket.accept()
        accepted.append(1)
        with first:
            first.recv(16)

        second, _ = server_socket.accept()
        accepted.append(2)
        with second:
            data = second.recv(16)
            if data == b"$I\n":
                second.sendall(b"ok\r\n")

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
    controller = GrblTelnetController(host, port=port, timeout=1)
    try:
        controller.connect()
        with pytest.raises(ConnectionError, match="connection closed"):
            controller.execute("$I")
        controller.connect()
        assert controller.execute("$I") == "ok"
    finally:
        controller.disconnect()
        server_socket.close()
        server_thread.join(timeout=1)

    assert accepted == [1, 2]
