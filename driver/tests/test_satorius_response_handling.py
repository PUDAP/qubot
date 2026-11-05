import logging
import time

import pytest

from qubot_drivers.rline import RLINE_SPECS, RLineModel
from qubot_drivers.satorius import SatoriusController, SatoriusDeviceError
from qubot_drivers.serialcontroller import SerialController


class FakeSerialResponse:
    """Serial response delivered in one or more chunks."""

    is_open = True

    def __init__(self, *chunks: bytes):
        self._chunks = list(chunks)

    @property
    def in_waiting(self) -> int:
        return len(self._chunks[0]) if self._chunks else 0

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0)


class StickyInWaitingSerial(FakeSerialResponse):
    """Model an adapter that keeps ``in_waiting`` truthy after frame delivery."""

    @property
    def in_waiting(self) -> int:
        return super().in_waiting or 1

    def read(self, _size: int) -> bytes:
        return super().read(_size) if self._chunks else b""


class RacyInWaitingSerial(FakeSerialResponse):
    """Model a byte count that changes between two property reads."""

    def __init__(self, *chunks: bytes):
        super().__init__(*chunks)
        self._next_read_has_bytes = True

    @property
    def in_waiting(self) -> int:
        if not self._chunks:
            return 0
        if self._next_read_has_bytes:
            self._next_read_has_bytes = False
            return len(self._chunks[0])
        self._next_read_has_bytes = True
        return 0

    def read(self, size: int) -> bytes:
        return super().read(size) if size else b""


def frame(payload: bytes, *, lrc: int | None = None) -> bytes:
    checksum = lrc
    if checksum is None:
        checksum = 0
        for byte in payload:
            checksum ^= byte
        checksum |= 0x80
    return b"\t" + payload + bytes([checksum]) + b"\r"


def make_controller() -> SatoriusController:
    controller = object.__new__(SatoriusController)
    controller._logger = logging.getLogger("test.sartorius")
    controller._volume = 0
    controller._timeout = 10
    controller._tip_attached = False
    controller.model = RLineModel.UL_5_200
    controller.spec = RLINE_SPECS[RLineModel.UL_5_200]
    return controller


def test_get_tracked_volume_returns_process_local_aspirated_volume() -> None:
    controller = make_controller()
    controller._volume = 321

    assert controller.get_tracked_volume() == 321


def test_execute_raises_on_sartorius_er2(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = make_controller()
    monkeypatch.setattr(
        SerialController,
        "execute",
        lambda self, command, value=None, timeout=None: "1er2",
    )

    with pytest.raises(SatoriusDeviceError, match="out-of-bounds"):
        controller.execute(command="RO", value="200")


def test_custom_volume_conversion_maps_1000_ul_to_400_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SerialController, "__init__", lambda self, *args, **kwargs: None)
    controller = SatoriusController(model=RLineModel.UL_50_1000)
    commands: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        controller,
        "execute",
        lambda command, value=None, timeout=None: commands.append((command, value)) or "ok",
    )

    controller.aspirate(1000)

    assert commands == [("RI", "400")]


def test_full_volume_dispense_uses_blowout(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = make_controller()
    controller._volume = 100
    commands: list[tuple[str, str | None]] = []
    position = 100

    def execute(command: str, value=None, timeout=None) -> str:
        nonlocal position
        commands.append((command, value))
        if command == "DP":
            return f"1dp{position}"
        if command == "DS":
            return "1ds0"
        if command == "RB":
            position = 0
        return "1ok"

    monkeypatch.setattr(controller, "execute", execute)

    controller.dispense(100)

    assert commands == [("RB", None), ("DS", None)]
    assert controller._volume == 0


def test_partial_dispense_uses_relative_outward_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = make_controller()
    controller._volume = 100
    commands: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        controller,
        "execute",
        lambda command, value=None: commands.append((command, value)) or "1ok",
    )

    controller.dispense(40)

    assert commands == [("RO", "80")]
    assert controller._volume == 60


def test_unterminated_position_reply_finishes_without_warning(caplog) -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    controller._serial = FakeSerialResponse(b"1dp443")

    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger="qubot_drivers.satorius"):
        response = controller._read_response(timeout=1)

    assert response == "1dp443"
    assert time.monotonic() - started < 0.5
    assert "unexpected response" not in caplog.text


def test_carriage_return_terminated_reply_finishes_without_timeout() -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    setattr(controller, "_serial", FakeSerialResponse(b"1dp-1\r"))

    started = time.monotonic()
    response = controller._read_response(timeout=1)

    assert response == "1dp-1"
    assert time.monotonic() - started < 0.5


def test_complete_frame_finishes_when_adapter_keeps_in_waiting_truthy() -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    setattr(controller, "_serial", StickyInWaitingSerial(b"1dp-1\r"))

    started = time.monotonic()
    response = controller._read_response(timeout=1)

    assert response == "1dp-1"
    assert time.monotonic() - started < 0.5


def test_read_uses_single_in_waiting_snapshot() -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    setattr(controller, "_serial", RacyInWaitingSerial(b"1dp-1\r"))

    started = time.monotonic()
    response = controller._read_response(timeout=1)

    assert response == "1dp-1"
    assert time.monotonic() - started < 0.5


def test_get_position_parses_sartorius_dp_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = make_controller()
    monkeypatch.setattr(controller, "execute", lambda command: "1dp443")

    assert controller.get_position() == 443


def test_get_device_info_queries_model_version_and_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = make_controller()
    responses = {"DM": "1dm710995", "DV": "1dv1025", "DP": "1dp30"}
    commands: list[str] = []

    def execute(command: str) -> str:
        commands.append(command)
        return responses[command]

    monkeypatch.setattr(controller, "execute", execute)

    assert controller.get_device_info() == {
        "model": "710995",
        "firmware_version": 1025,
        "position_steps": 30,
        "tracked_volume_ul": 0,
    }
    assert commands == ["DM", "DV", "DP"]


def test_get_device_info_rejects_malformed_identity_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = make_controller()
    monkeypatch.setattr(controller, "execute", lambda command: "1ok")

    with pytest.raises(SatoriusDeviceError, match="model"):
        controller.get_device_info()


def test_unterminated_alphanumeric_model_reply_finishes_without_timeout() -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    setattr(controller, "_serial", FakeSerialResponse(b"1dmBRL1000-1"))

    started = time.monotonic()
    response = controller._read_response(timeout=1)

    assert response == "1dmBRL1000-1"
    assert time.monotonic() - started < 0.5


def test_rejected_standalone_blowout_preserves_volume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = make_controller()
    controller._volume = 275

    def execute(command: str, value=None) -> str:
        if command == "DP":
            return "1dp140"
        raise SatoriusDeviceError(
            "Sartorius rejected RB: er2 (command would result in an out-of-bounds state)"
        )

    monkeypatch.setattr(controller, "execute", execute)

    with pytest.raises(SatoriusDeviceError, match="er2"):
        controller.run_blowout()

    assert controller.get_tracked_volume() == 275


def test_native_framed_reply_finishes_without_serial_timeout() -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    controller._serial = FakeSerialResponse(frame(b"1dp30"))
    started = time.monotonic()
    assert controller._read_response(timeout=1) == "1dp30"
    assert time.monotonic() - started < 0.5


@pytest.mark.parametrize("payload", [b"1dp30", b"1dmBRL1000-1", b"1er4"])
def test_native_fragmented_reply_waits_for_checksum_and_terminator(payload) -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=1)
    raw = frame(payload)
    controller._serial = FakeSerialResponse(raw[:5], raw[5:-1], raw[-1:])
    assert controller._read_response(timeout=1) == payload.decode("ascii")


@pytest.mark.parametrize("raw", [frame(b"1dp30", lrc=0x80), b"\t1dp30", frame(b"2dp30")])
def test_native_invalid_reply_never_becomes_position(raw) -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=0.02)
    controller._serial = FakeSerialResponse(raw)
    with pytest.raises((SatoriusDeviceError, TimeoutError)):
        controller._read_response(timeout=0.02)


def test_home_drive_error_blocks_position_acceptance(monkeypatch) -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200)
    monkeypatch.setattr(controller, "execute", lambda command, value=None, timeout=None: "1ds8" if command == "DS" else "1ok")
    with pytest.raises(SatoriusDeviceError, match="status"):
        controller.run_to_position(30)


def test_completion_status_has_bounded_deadline(monkeypatch) -> None:
    controller = SatoriusController(port_name="fake", model=RLineModel.UL_5_200, timeout=0.02)
    calls = []
    def execute(command, value=None, timeout=None):
        calls.append(command)
        return "1ds2" if command == "DS" else "1ok"
    monkeypatch.setattr(controller, "execute", execute)
    with pytest.raises(SatoriusDeviceError, match="timed out"):
        controller.run_to_position(30)
    assert calls.count("RP") == 1
    assert "DP" not in calls
