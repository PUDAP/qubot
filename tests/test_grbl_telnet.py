"""NETCON payload and reply assembly. No socket is opened."""

from queue import Queue

import pytest

from qubot.gantry.grbl_telnet import GrblTelnetController, telnet_payload


def test_realtime_bytes_have_no_line_feed():
    assert telnet_payload("?") == b"?"
    assert telnet_payload("!") == b"!"
    assert telnet_payload("~") == b"~"


def test_motion_lines_use_netcon_line_feed():
    assert telnet_payload("$H") == b"$H\n"
    assert telnet_payload("M8\r") == b"M8\n"


def test_reply_keeps_lines_before_ok():
    controller = GrblTelnetController("192.0.2.1")
    queue: Queue[str] = Queue()
    queue.put("[VER:1.1f]")
    queue.put("ok")
    assert controller._read_ok(queue, timeout=1) == "[VER:1.1f]\nok"


def test_alarm_raises():
    controller = GrblTelnetController("192.0.2.1")
    queue: Queue[str] = Queue()
    queue.put("ALARM:1")
    with pytest.raises(RuntimeError, match="ALARM:1"):
        controller._read_ok(queue, timeout=1)
