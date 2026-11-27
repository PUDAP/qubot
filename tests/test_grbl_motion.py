"""Opt-in motion. Defaults stay the released safe-height path and 3000 mm/min."""

from qubot.gantry.grbl import GrblHALController
from qubot.gantry.grbl_telnet import GrblTelnetController
from qubot.geometry import Position


class _RecordingGantry(GrblHALController):
    def __init__(self, **kwargs):
        super().__init__(port_name="unused", **kwargs)
        self.sent: list[str] = []
        self.set_axis_limits("X", -1000, 1000)
        self.set_axis_limits("Y", -1000, 1000)
        self.set_axis_limits("Z", -1000, 1000)

    def execute(self, command: str, value=None, timeout=None) -> str:
        del value, timeout
        self.sent.append(command)
        if command == "$$":
            return "$110=2000\n$111=1500\n$112=800\nok"
        return "ok"


def test_defaults_stay_3000_and_safe_height():
    gantry = _RecordingGantry()
    assert gantry.feed == 3000
    assert gantry._z_motion == "safe_height"
    gantry._current_position = Position(x=0, y=0, z=0)
    gantry.move_absolute(Position(x=10, y=0, z=0), apply_safe_z=True)
    assert gantry.sent[1].startswith("G1 Z-5")


def test_directional_rises_before_xy_and_descends_after():
    rising = _RecordingGantry(feed=600, z_motion="directional")
    rising._current_position = Position(x=0, y=0, z=-20)
    rising.move_absolute(Position(x=10, y=0, z=-5))
    motion = [line for line in rising.sent if line.startswith("G1")]
    assert motion[0].startswith("G1 Z-5")
    assert "X10" in motion[1]

    falling = _RecordingGantry(feed=600, z_motion="directional")
    falling._current_position = Position(x=0, y=0, z=-5)
    falling.move_absolute(Position(x=10, y=0, z=-20))
    motion = [line for line in falling.sent if line.startswith("G1")]
    assert "X10" in motion[0]
    assert motion[1].startswith("G1 Z-20")


def test_feed_ceiling_comes_from_settings():
    gantry = _RecordingGantry(feed=3000)
    assert gantry.read_hardware_feed_limits() == 1500
    assert gantry.feed == 1500
    assert gantry._z_feed == 800


class _Socket:
    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)


def test_telnet_forwards_feed_and_sends_immediate_without_a_lock():
    plain = GrblTelnetController("192.0.2.1")
    assert plain.feed == 3000
    assert plain._z_motion == "safe_height"

    controller = GrblTelnetController("192.0.2.1", feed=600, z_motion="directional")
    socket = _Socket()
    controller._socket = socket
    controller._telnet_connected = True
    controller.send_immediate("M9")
    assert socket.sent == [b"M9\n"]
    assert controller.feed == 600
