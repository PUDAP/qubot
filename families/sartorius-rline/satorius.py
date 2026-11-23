"""
Satorius rLINE pipette controller.

Reference: https://api.sartorius.com/document-hub/dam/download/34901/Sartorius-rLine-technical-user-manual-v1.1.pdf
"""

import json
import logging
import re
import time
from typing import Dict, Optional

from qubot_drivers.rline import RLINE_SPECS, RLineModel, RLineSpec
from qubot_drivers.serialcontroller import SerialController

STATUS_CODES: Dict[str, str] = {
    "0": "No Errors. Module Ready for Commands",
    "1": "Drive Brake is On",
    "2": "Command Received, Running",
    "4": "Drive is On",
    "6": "Drive + Running busy.",
    "8": "General error. Drive has not successfully completed last command",
}


class SatoriusDeviceError(Exception):
    """Custom exception raised when the Satorius device reports an error."""


class SatoriusController(SerialController):
    """Controller for Satorius rLINE pipettes and robotic dispensers."""

    DEFAULT_BAUDRATE = 9600
    DEFAULT_TIMEOUT = 10

    PROTOCOL_SOH = "\x01"
    SLAVE_ADDRESS = "1"
    PROTOCOL_TERMINATOR = "º\r"

    SUCCESS_RESPONSE = "ok"
    ERROR_RESPONSE = "err"
    MIN_SPEED = 1
    MAX_SPEED = 6
    RESPONSE_PATTERN_BYTES = re.compile(
        rb"^\x01?1(?:ok|er[1-4]|[a-z]{2}[a-z0-9._-]+)$",
        re.IGNORECASE,
    )
    RESPONSE_PATTERN_TEXT = re.compile(
        r"^\x01?1(?:ok|er[1-4]|[a-z]{2}[a-z0-9._-]+)$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        port_name: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: int = DEFAULT_TIMEOUT,
        *,
        model: RLineModel,
    ):
        super().__init__(port_name, baudrate, timeout)
        try:
            spec = RLINE_SPECS[model]
        except KeyError as exc:
            raise ValueError(f"Unknown rLine model: {model!r}") from exc

        self._logger = logging.getLogger("qubot_drivers.satorius")
        self._logger.info(
            "Satorius Controller initialized with port='%s', baudrate=%s, timeout=%s, model=%s",
            port_name,
            baudrate,
            timeout,
            model.value,
        )
        self._tip_attached: bool = False
        self._volume: int = 0
        self.model = model
        self.spec: RLineSpec = spec

    def _steps_for_volume(self, amount: int, command_name: str) -> int:
        steps = int(amount / self.spec.microliters_per_step)
        if steps > self.spec.max_position:
            raise ValueError(
                f"{command_name} of {amount} uL is {steps} steps, past "
                f"{self.model.value} max position {self.spec.max_position}"
            )
        return steps

    def _is_complete_unterminated_response(self, response: bytes) -> bool:
        normalized = response.rstrip(b"\r\n")
        return self.RESPONSE_PATTERN_BYTES.fullmatch(normalized) is not None

    def _is_expected_response(self, response: str) -> bool:
        return self.RESPONSE_PATTERN_TEXT.fullmatch(response) is not None

    def _read_response(self, timeout: Optional[float] = None) -> str:
        """Read rLine HT/address/payload/LRC/CR before decoding any bytes.

        The generic reader cannot identify binary LRC frames reliably. Legacy
        unframed adapters are supported only after CR or a bounded quiet period;
        a numeric prefix alone is never evidence of a complete native frame.
        """
        if not self.is_connected or self._serial is None:
            raise SatoriusDeviceError("Pipette serial port is disconnected")
        deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
        raw = b""
        last_byte_at = None
        while time.monotonic() < deadline:
            waiting = self._serial.in_waiting
            chunk = self._serial.read(waiting) if waiting else b""
            if chunk:
                raw += chunk
                last_byte_at = time.monotonic()
                if raw.startswith(b"\t") and b"\r" in raw:
                    packet, trailing = raw.split(b"\r", 1)
                    if trailing.strip(b"\n") or len(packet) < 5:
                        raise SatoriusDeviceError(f"Invalid rLine frame: {raw!r}")
                    payload, received_lrc = packet[1:-1], packet[-1]
                    expected_lrc = 0
                    for byte in payload:
                        expected_lrc ^= byte
                    if received_lrc != (expected_lrc | 0x80):
                        raise SatoriusDeviceError(f"Invalid rLine checksum: {raw!r}")
                    try:
                        text = payload.decode("ascii")
                    except UnicodeDecodeError as exc:
                        raise SatoriusDeviceError(f"Invalid rLine payload: {raw!r}") from exc
                    if not self._is_expected_response(text):
                        raise SatoriusDeviceError(f"Invalid rLine address/payload: {raw!r}")
                    self._logger.debug("<- Received raw frame %r; payload %r", raw, text)
                    return text
                if not raw.startswith(b"\t") and b"\r" in raw:
                    break
            elif (raw and not raw.startswith(b"\t") and last_byte_at is not None
                  and time.monotonic() - last_byte_at >= 0.03):
                break
            time.sleep(0.005)
        if not raw or raw.startswith(b"\t"):
            raise SatoriusDeviceError(f"Incomplete rLine response before deadline: {raw!r}")
        try:
            text = raw.rstrip(b"\r\n").decode("ascii")
        except UnicodeDecodeError as exc:
            raise SatoriusDeviceError(f"Invalid unframed rLine response: {raw!r}") from exc
        if not self._is_expected_response(text):
            raise SatoriusDeviceError(f"Invalid unframed rLine response: {raw!r}")
        self._logger.debug("<- Received unframed response: %r", text)
        return text

    def _wait_ready(self, timeout: Optional[float] = None) -> None:
        """An OK acknowledges receipt, not motion completion (manual p18)."""
        deadline = time.monotonic() + (self._timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            response = self.execute(command="DS", timeout=max(0.001, deadline - time.monotonic()))
            if response == "1ds0":
                return
            if response not in {"1ds1", "1ds2", "1ds4", "1ds6"}:
                raise SatoriusDeviceError(f"Pipette completion status failure: {response}")
            time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
        raise SatoriusDeviceError("Pipette completion status timed out; no automatic retry")

    def _build_command(self, command: str, value: Optional[str] = None) -> str:
        return (
            self.PROTOCOL_SOH
            + self.SLAVE_ADDRESS
            + command
            + (f"{value}" if value else "")
            + self.PROTOCOL_TERMINATOR
        )

    def execute(
        self,
        command: str,
        value: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        if timeout is None:
            response = super().execute(command=command, value=value)
        else:
            response = super().execute(command=command, value=value, timeout=timeout)
        match = re.search(r"er([1-4])", response.lower())
        if match:
            error_messages = {
                "1": "command not understood",
                "2": "command would result in an out-of-bounds state",
                "3": "checksum mismatch",
                "4": "drive is busy and cannot answer the command",
            }
            error_code = match.group(1)
            raise SatoriusDeviceError(
                f"Sartorius rejected {command}: er{error_code} "
                f"({error_messages[error_code]})"
            )
        return response

    def _validate_speed(self, speed: int, direction: str = "speed") -> None:
        if not self.MIN_SPEED <= speed <= self.MAX_SPEED:
            raise ValueError(
                f"{direction} speed must be between {self.MIN_SPEED} and {self.MAX_SPEED}, "
                f"got {speed}"
            )

    def _validate_no_leading_zeros(self, value: int, command_name: str) -> str:
        value_str = str(value)
        if len(value_str) > 1 and value_str.startswith("0"):
            raise ValueError(
                f"{command_name} command value must not have leading zeros. "
                f"Got: {value_str}"
            )
        return value_str

    def _reset_volume(self) -> None:
        self._volume = 0

    def initialize(self) -> None:
        self._logger.info("** Initializing Pipette Head (RZ) **")
        self.execute(command="RZ")
        self._logger.info("** Pipette Initialization Complete **\n")
        self.set_tip_attached(attached=False)
        self._reset_volume()

    def get_inward_speed(self) -> int:
        self._logger.info("** Querying Inward Speed (DI) **")
        response = self.execute(command="DI")

        if len(response) < 2:
            raise SatoriusDeviceError(
                f"Invalid response format for inward speed query: {response}"
            )

        speed = int(response[1])
        self._logger.info("** Current Inward Speed: %s **\n", speed)
        return speed

    def set_inward_speed(self, speed: int) -> None:
        self._validate_speed(speed, "Inward")
        self._logger.info("** Setting Inward Speed (SI, Speed: %s) **", speed)
        self.execute(command="SI", value=str(speed))
        self._logger.info("** Inward Speed Set to %s Successfully **\n", speed)

    def get_outward_speed(self) -> int:
        self._logger.info("** Querying Outward Speed (DO) **")
        response = self.execute(command="DO")

        if len(response) < 2:
            raise SatoriusDeviceError(
                f"Invalid response format for outward speed query: {response}"
            )

        speed = int(response[1])
        self._logger.info("** Current Outward Speed: %s **\n", speed)
        return speed

    def set_outward_speed(self, speed: int) -> None:
        self._validate_speed(speed, "Outward")
        self._logger.info("** Setting Outward Speed (SO, Speed: %s) **", speed)
        self.execute(command="SO", value=str(speed))
        self._logger.info("** Outward Speed Set to %s Successfully **\n", speed)

    def run_to_position(self, position: int) -> None:
        position_str = self._validate_no_leading_zeros(position, "RP")
        self._logger.info("** Run to absolute Position (RP, Position: %s) **", position)
        self.execute(command="RP", value=position_str)
        self._wait_ready()
        self._logger.info("** Reached Position %s Successfully **\n", position)

    def aspirate(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError(f"Aspiration amount must be positive, got {amount}")

        steps = self._steps_for_volume(amount, "RI")
        self._logger.info("** Aspirating %s uL (RI%s steps) **", amount, steps)
        self.execute(command="RI", value=str(steps))
        self._logger.info("** Aspirated %s uL Successfully **\n", amount)
        self._volume += amount

    def dispense(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError(f"Dispense amount must be positive, got {amount}")

        if amount == self._volume:
            self._logger.info(
                "** Dispensing full aspirated volume %s uL with blowout (RB) **",
                amount,
            )
            self.run_blowout()
            self._reset_volume()
            self._logger.info("** Dispensed %s uL Successfully **\n", amount)
            return

        steps = self._steps_for_volume(amount, "RO")
        self._logger.info("** Dispensing %s uL (RO%s steps) **", amount, steps)
        self.execute(command="RO", value=str(steps))
        self._logger.info("** Dispensed %s uL Successfully **\n", amount)
        self._volume -= amount

    def eject_tip(self, return_position: Optional[int] = None) -> None:
        if return_position is None:
            return_position = self.spec.home_position
        position_str = self._validate_no_leading_zeros(
            command_name="RE",
            value=return_position,
        )
        self._logger.info(
            "** Ejecting Tip and returning to position %s (RE %s) **",
            return_position,
            return_position,
        )
        self.execute(command="RE", value=position_str)
        self._logger.info("** Tip Ejection Complete **\n")

    def run_blowout(self, return_position: Optional[int] = None) -> None:
        if return_position is not None:
            position_str = self._validate_no_leading_zeros(return_position, "RB")
            self._logger.info(
                "** Running Blowout and returning to position %s (RB%s) **",
                return_position,
                return_position,
            )
            self.execute(command="RB", value=position_str)
        else:
            self._logger.info("** Running Blowout (RB) **")
            self.execute(command="RB")

        self._wait_ready()
        self._logger.info("** Blowout Complete **\n")

    def get_status(self) -> str:
        self._logger.info("** Querying Pipette Status (DS) **")
        response = self.execute(command="DS")

        if len(response) < 2:
            raise SatoriusDeviceError(
                f"Invalid response format for status query: {response}"
            )

        status_code = response[1]
        status_data = {
            "status_code": status_code,
            "is_known": status_code in STATUS_CODES,
        }

        if status_code in STATUS_CODES:
            status_message = STATUS_CODES[status_code]
            status_data["status_message"] = status_message
            self._logger.info("Pipette Status Code [%s]: %s\n", status_code, status_message)
        else:
            status_data["status_message"] = None
            self._logger.warning(
                "Pipette Status Code [%s]: Unknown Status Code\n", status_code
            )

        return json.dumps(status_data)

    def get_position(self) -> int:
        self._logger.info("** Querying Position (DP) **")
        response = self.execute(command="DP")
        match = re.fullmatch(r"\x01?1dp(-?\d+)", response, re.IGNORECASE)
        if match is None:
            raise SatoriusDeviceError(
                f"Invalid response format for position query: {response}"
            )
        position = int(match.group(1))
        self._logger.info("** Position: %s steps **\n", position)
        return position

    def get_model(self) -> str:
        """Return the rLine model/catalog identifier reported by ``DM``."""
        response = self.execute(command="DM")
        match = re.fullmatch(r"\x01?1dm([A-Za-z0-9._-]+)", response, re.IGNORECASE)
        if match is None:
            raise SatoriusDeviceError(
                f"Invalid response format for model query: {response}"
            )
        return match.group(1)

    def get_firmware_version(self) -> int:
        """Return the numeric firmware version reported by ``DV``."""
        response = self.execute(command="DV")
        match = re.fullmatch(r"\x01?1dv(\d+)", response, re.IGNORECASE)
        if match is None:
            raise SatoriusDeviceError(
                f"Invalid response format for firmware version query: {response}"
            )
        return int(match.group(1))

    def get_device_info(self) -> Dict[str, int | str]:
        """Return read-only identity, position, and process-local volume state."""
        return {
            "model": self.get_model(),
            "firmware_version": self.get_firmware_version(),
            "position_steps": self.get_position(),
            "tracked_volume_ul": self.get_tracked_volume(),
        }

    def get_liquid_level(self) -> int:
        self._logger.info("** Querying Liquid Level (DN) **")
        response = self.execute(command="DN")
        self._logger.info("** Liquid Level: %s uL **\n", response)
        return response

    def is_tip_attached(self) -> bool:
        return self._tip_attached

    def get_tracked_volume(self) -> int:
        """Return the process-local aspirated liquid volume in microlitres."""
        return self._volume

    def set_tip_attached(self, attached: bool) -> None:
        self._tip_attached = attached
