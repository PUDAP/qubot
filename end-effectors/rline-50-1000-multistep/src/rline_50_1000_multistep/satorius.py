"""
Satorius rLINE pipette controller.

Reference: https://api.sartorius.com/document-hub/dam/download/34901/Sartorius-rLine-technical-user-manual-v1.1.pdf
"""

import json
import logging
import re
import time
from typing import Dict, Optional

from .pace import RESPONSE_TIME_S, STEP_RESOLUTION, plan_transfer, remaining_pause
from .rline import RLINE_SPECS, RLineModel, RLineSpec
from .serialcontroller import SerialController

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
    """50-1000 uL rLine controller that can pace aspirate and dispense speed."""

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
        step_resolution: int = STEP_RESOLUTION,
        response_time_s: float = RESPONSE_TIME_S,
    ):
        super().__init__(port_name, baudrate, timeout)
        if model is not RLineModel.UL_50_1000:
            raise ValueError(
                "rline-50-1000-multistep drives the 50-1000 uL body only, "
                f"got {getattr(model, 'value', model)!r}"
            )
        if isinstance(step_resolution, bool) or not isinstance(step_resolution, int) or step_resolution < 1:
            raise ValueError(f"step_resolution must be a positive integer, got {step_resolution!r}")
        if (
            isinstance(response_time_s, bool)
            or not isinstance(response_time_s, (int, float))
            or float(response_time_s) <= 0
        ):
            raise ValueError(f"response_time_s must be positive, got {response_time_s!r}")
        try:
            spec = RLINE_SPECS[model]
        except KeyError as exc:
            raise ValueError(f"Unknown rLine model: {model!r}") from exc

        self._logger = logging.getLogger("rline_50_1000_multistep")
        self._logger.info(
            "Satorius Controller initialized with port='%s', baudrate=%s, timeout=%s, model=%s",
            port_name,
            baudrate,
            timeout,
            model.value,
        )
        self._tip_attached: bool = False
        self._volume: float = 0.0
        self.model = model
        self.spec: RLineSpec = spec
        self.step_resolution = step_resolution
        self.response_time_s = float(response_time_s)
        # Speed setting 3 until set_inward_speed / set_outward_speed says otherwise.
        self._inward_code = 3
        self._outward_code = 3
        self._inward_synced = False
        self._outward_synced = False
        self._sleep = time.sleep
        self._monotonic = time.perf_counter

    def _checked_volume(self, amount: float, command_name: str, minimum_ul: float) -> tuple[int, float]:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"{command_name} volume must be microliters, got {amount!r}")
        if amount <= 0:
            raise ValueError(f"{command_name} volume must be positive, got {amount}")
        quantum = self.spec.microliters_per_step
        steps = int(round(float(amount) / quantum))
        actual = steps * quantum
        if abs(actual - float(amount)) > 1e-6:
            raise ValueError(
                f"{command_name} volume must be a multiple of {quantum:g} uL "
                f"on the {self.model.value} pipette, got {amount}"
            )
        if actual < minimum_ul - 1e-6 or actual > self.spec.maximum_volume_ul + 1e-6:
            raise ValueError(
                f"{command_name} volume must be between {minimum_ul:g} and "
                f"{self.spec.maximum_volume_ul} uL on the {self.model.value} pipette, got {actual:g}"
            )
        if steps > self.spec.max_position:
            raise ValueError(
                f"{command_name} of {actual:g} uL is {steps} steps, past "
                f"{self.model.value} max position {self.spec.max_position}"
            )
        return steps, actual

    def _requested_speed(self, speed_ul_s: Optional[float], direction: str) -> float:
        if speed_ul_s is None:
            code = self._inward_code if direction == "in" else self._outward_code
            return self.spec.microliters_per_second[code - 1]
        if isinstance(speed_ul_s, bool) or not isinstance(speed_ul_s, (int, float)) or speed_ul_s <= 0:
            raise ValueError(
                f"speed_ul_s must be positive microliters per second, got {speed_ul_s!r}"
            )
        return speed_ul_s

    def _ensure_speed(self, direction: str, code: int) -> None:
        if direction == "in":
            if self._inward_synced and self._inward_code == code:
                return
            self.set_inward_speed(code)
            return
        if self._outward_synced and self._outward_code == code:
            return
        self.set_outward_speed(code)

    def _run_intervals(self, command: str, plan: dict, sign: int) -> None:
        """Send each chunk, then wait until that chunk's apparent-speed window ends."""
        self._logger.info(
            "Paced %s of %s uL at %s uL/s as preset %s uL/s, steps %s, pause %s s",
            command,
            plan["volume_ul"],
            plan["speed_ul_s"],
            plan["preset_speed"],
            plan["steps"],
            plan["delay"],
        )
        for step in plan["steps"]:
            started = self._monotonic()
            self.execute(command=command, value=str(int(step)))
            move_time = step * self.spec.microliters_per_step / plan["preset_speed"]
            self._wait_ready(
                timeout=max(float(self._timeout), move_time + self.response_time_s + 2.0)
            )
            self._volume += sign * step * self.spec.microliters_per_step
            pause = remaining_pause(self._monotonic() - started, move_time, plan["delay"])
            if pause > 0:
                self._sleep(pause)

    def _move_liquid(
        self,
        command: str,
        actual_ul: float,
        speed_ul_s: Optional[float],
        direction: str,
    ) -> dict:
        speed = self._requested_speed(speed_ul_s, direction)
        plan = plan_transfer(
            actual_ul,
            speed,
            microliters_per_step=self.spec.microliters_per_step,
            speed_presets=self.spec.microliters_per_second,
            step_resolution=self.step_resolution,
            response_time_s=self.response_time_s,
        )
        code = self.spec.microliters_per_second.index(plan["preset_speed"]) + 1
        previous = self._inward_code if direction == "in" else self._outward_code
        sign = 1 if command == "RI" else -1
        try:
            self._ensure_speed(direction, code)
            self._run_intervals(command, plan, sign)
        finally:
            if previous != code:
                self._ensure_speed(direction, previous)
        plan["speed_code"] = code
        return plan

    def _result(self, plan: dict, *, blowout: bool) -> dict:
        return {
            "volume_ul": plan["volume_ul"],
            "speed_ul_s": plan["speed_ul_s"],
            "preset_speed_ul_s": plan["preset_speed"],
            "speed_code": plan["speed_code"],
            "n_intervals": plan["n_intervals"],
            "steps": list(plan["steps"]),
            "delay_s": plan["delay"],
            "blowout": blowout,
            "tracked_volume_ul": self.get_tracked_volume(),
        }

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
        self._volume = 0.0

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
        self._inward_code = speed
        self._inward_synced = True
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
        self._outward_code = speed
        self._outward_synced = True
        self._logger.info("** Outward Speed Set to %s Successfully **\n", speed)

    def run_to_position(self, position: int) -> None:
        position_str = self._validate_no_leading_zeros(position, "RP")
        self._logger.info("** Run to absolute Position (RP, Position: %s) **", position)
        self.execute(command="RP", value=position_str)
        self._wait_ready()
        self._logger.info("** Reached Position %s Successfully **\n", position)

    def aspirate(self, amount: float, speed_ul_s: Optional[float] = None) -> dict:
        """Aspirate ``amount`` microliters at an apparent speed of ``speed_ul_s``.

        Omit ``speed_ul_s`` to use the current inward preset. The 50-1000 uL
        body accepts 50 to 1000 uL in steps of 2.5 uL. A speed that is not one
        of the six presets is split across a faster preset.
        """
        minimum = max(
            self.spec.minimum_volume_ul,
            self.step_resolution * self.spec.microliters_per_step,
        )
        _steps, actual = self._checked_volume(amount, "Aspirate", minimum)
        if self._volume + actual > self.spec.maximum_volume_ul + 1e-6:
            raise ValueError(
                f"Aspirate of {actual:g} uL would pass the {self.spec.maximum_volume_ul} uL "
                f"capacity ({self.get_tracked_volume()} uL is already tracked)"
            )
        plan = self._move_liquid("RI", actual, speed_ul_s, "in")
        return self._result(plan, blowout=False)

    def dispense(self, amount: float, speed_ul_s: Optional[float] = None) -> dict:
        """Dispense ``amount`` microliters at an apparent speed of ``speed_ul_s``.

        Omit ``speed_ul_s`` to use the current outward preset. Dispensing the
        entire tracked volume paces the outward steps and then runs blowout.
        """
        minimum = max(
            self.spec.microliters_per_step,
            self.step_resolution * self.spec.microliters_per_step,
        )
        _steps, actual = self._checked_volume(amount, "Dispense", minimum)
        if actual > self._volume + 1e-6:
            raise ValueError(
                f"Dispense of {actual:g} uL exceeds the tracked {self.get_tracked_volume()} uL"
            )
        emptying = abs(actual - self._volume) <= 1e-6
        plan = self._move_liquid("RO", actual, speed_ul_s, "out")
        if emptying:
            self.run_blowout()
            self._reset_volume()
        return self._result(plan, blowout=emptying)

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

    def get_tracked_volume(self) -> int | float:
        """Return the process-local aspirated liquid volume in microlitres."""
        if abs(self._volume - round(self._volume)) < 1e-6:
            return int(round(self._volume))
        return self._volume

    def set_tip_attached(self, attached: bool) -> None:
        self._tip_attached = attached
