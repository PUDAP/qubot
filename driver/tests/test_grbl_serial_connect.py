from qubot_drivers.move.grblHAL import GrblHALController
from qubot_drivers import serialcontroller


class FakeSerial:
    instances = []

    def __init__(self, *args, **kwargs):
        self.port = kwargs.get("port")
        self.baudrate = kwargs.get("baudrate")
        self.timeout = kwargs.get("timeout")
        self.dtr = True
        self.rts = True
        self.is_open = bool(self.port)
        self.opened_with = (self.dtr, self.rts) if self.is_open else None
        self._boot = bytearray(b"GrblHAL 1.1f\r\n")
        self.flushed = False
        FakeSerial.instances.append(self)

    def open(self):
        self.opened_with = (self.dtr, self.rts)
        self.is_open = True

    def flush(self):
        self.flushed = True

    @property
    def in_waiting(self):
        return len(self._boot)

    def read(self, size):
        data = bytes(self._boot[:size])
        del self._boot[:size]
        return data


def test_grbl_connect_disables_control_lines_before_open_and_drains_boot(monkeypatch):
    FakeSerial.instances.clear()
    sleeps = []
    monkeypatch.setattr(serialcontroller.serial, "Serial", FakeSerial)
    monkeypatch.setattr(serialcontroller.time, "sleep", sleeps.append)

    controller = GrblHALController(port_name="/dev/ttyUSB0")
    controller.connect()

    serial_port = FakeSerial.instances[-1]
    assert serial_port.opened_with == (False, False)
    assert sleeps == [3.0]
    assert serial_port.in_waiting == 0
    assert serial_port.flushed is True
