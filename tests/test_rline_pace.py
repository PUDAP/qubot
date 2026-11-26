"""The 50-1000 uL body paces speed without changing its volume scale."""

import pytest

from qubot.end_effector.rline_50_1000_multistep import (
    MAXIMUM_VOLUME_UL,
    MICROLITERS_PER_STEP,
    MINIMUM_VOLUME_UL,
    MODEL,
    connect,
)
from qubot.end_effector.rline_pace import interpolate_speed, plan_transfer
from qubot.end_effector.rline import RLINE_SPECS, RLineModel
from qubot.end_effector.satorius_multistep import SatoriusController, SatoriusDeviceError

PRESETS = (150, 265, 410, 650, 945, 1120)
# The calibration measured on the PESCador pipette; an edge passes its own.
CAL = {"step_resolution": 10, "response_time_s": 1.03}


def test_selected_body_is_the_50_1000_microliter_pipette():
    spec = RLINE_SPECS[MODEL]
    assert MODEL is RLineModel.UL_50_1000
    assert MODEL.value == "50-1000"
    assert MINIMUM_VOLUME_UL == 50
    assert MAXIMUM_VOLUME_UL == 1000
    assert MICROLITERS_PER_STEP == 2.5
    assert spec.minimum_volume_ul == 50
    assert spec.maximum_volume_ul == 1000
    assert spec.microliters_per_step == 2.5
    assert spec.home_position == 30
    assert spec.max_position == 443
    assert spec.tip_eject_position == -40
    assert spec.microliters_per_second == PRESETS
    assert RLINE_SPECS[RLineModel.UL_5_200].microliters_per_step == 0.5
    assert RLINE_SPECS[RLineModel.UL_100_5000].microliters_per_step == 10


def test_other_rline_models_are_refused():
    with pytest.raises(ValueError, match="50-1000"):
        SatoriusController(port_name="unused", model=RLineModel.UL_5_200, **CAL)
    with pytest.raises(ValueError, match="50-1000"):
        SatoriusController(port_name="unused", model=RLineModel.UL_100_5000, **CAL)


def test_connect_keeps_the_calibration_arguments():
    pipette = connect("unused", step_resolution=12, response_time_s=0.8)
    assert pipette.model is RLineModel.UL_50_1000
    assert pipette.spec.maximum_volume_ul == 1000
    assert pipette.step_resolution == 12
    assert pipette.response_time_s == 0.8


def test_preset_speed_is_one_interval():
    plan = plan_transfer(
        200,
        410,
        microliters_per_step=2.5,
        speed_presets=PRESETS,
        step_resolution=CAL["step_resolution"],
        response_time_s=CAL["response_time_s"],
    )
    assert plan["n_intervals"] == 1
    assert plan["steps"] == [80]
    assert plan["delay"] == 0
    assert plan["preset_speed"] == 410


def test_1000_ul_at_200_ul_s_uses_the_650_preset_in_three_chunks():
    plan = plan_transfer(
        1000,
        200,
        microliters_per_step=2.5,
        speed_presets=PRESETS,
        step_resolution=CAL["step_resolution"],
        response_time_s=CAL["response_time_s"],
    )
    assert plan["preset_speed"] == 650
    assert plan["n_intervals"] == 3
    assert plan["steps"] == [133, 133, 134]
    assert sum(plan["steps"]) == 400
    expected_delay = 1000 * (1 / 200 - 1 / 650) / 3
    assert plan["delay"] == pytest.approx(expected_delay)
    motion = 1000 / 650
    assert motion + 3 * plan["delay"] == pytest.approx(1000 / 200)


def test_speed_between_presets_is_refused_when_the_pause_is_shorter_than_the_response():
    with pytest.raises(ValueError, match="No multistep plan"):
        plan_transfer(
            200,
            300,
            microliters_per_step=2.5,
            speed_presets=PRESETS,
            response_time_s=1.03,
            step_resolution=CAL["step_resolution"],
        )


def test_a_longer_response_time_refuses_a_plan_the_default_calibration_accepts():
    with pytest.raises(ValueError, match="No multistep plan"):
        plan_transfer(
            1000,
            200,
            microliters_per_step=2.5,
            speed_presets=PRESETS,
            response_time_s=10,
            step_resolution=CAL["step_resolution"],
        )


def test_volume_below_step_resolution_is_not_interpolated():
    raw = interpolate_speed(
        20,
        410,
        speed_presets=PRESETS,
        volume_resolution=2.5,
        step_resolution=10,
        time_resolution=1.03,
    )
    assert raw["n_intervals"] == 0


class ScriptedPipette(SatoriusController):
    """Records commands and advances a fake clock by 50 ms per exchange."""

    def __init__(self, **kwargs):
        super().__init__(port_name="scripted", model=RLineModel.UL_50_1000, **{**CAL, **kwargs})
        self.commands: list[tuple[str, str | None]] = []
        self._now = 0.0
        self._sleep = self._advance
        self._monotonic = lambda: self._now

    def _advance(self, seconds: float) -> None:
        self._now += seconds

    def execute(self, command: str, value: str | None = None, timeout: float | None = None) -> str:
        del timeout
        self.commands.append((command, None if value is None else str(value)))
        self._now += 0.05
        if command == "DS":
            return "1ds0"
        return "1ok"

    def _wait_ready(self, timeout: float | None = None) -> None:
        del timeout
        self.execute(command="DS")


def _values(pipette: ScriptedPipette, command: str) -> list[str]:
    return [value for name, value in pipette.commands if name == command and value is not None]


def test_200_ul_is_80_steps_not_the_neighboring_models():
    pipette = ScriptedPipette()
    result = pipette.aspirate(200)
    assert _values(pipette, "RI") == ["80"]
    assert result["tracked_volume_ul"] == 200
    assert result["n_intervals"] == 1
    assert result["blowout"] is False


def test_paced_aspirate_hits_the_requested_wall_clock_speed():
    pipette = ScriptedPipette()
    result = pipette.aspirate(1000, 200)
    assert result["preset_speed_ul_s"] == 650
    assert result["speed_code"] == 4
    assert _values(pipette, "RI") == ["133", "133", "134"]
    assert sum(int(step) for step in _values(pipette, "RI")) == 400
    assert [name for name, _value in pipette.commands if name == "SI"] == ["SI", "SI"]
    assert _values(pipette, "SI") == ["4", "3"]
    speed_commands = sum(1 for name, _value in pipette.commands if name == "SI")
    assert pipette._now == pytest.approx(1000 / 200 + 0.05 * speed_commands)


def test_a_failed_chunk_keeps_the_volume_already_taken_and_restores_speed():
    class StopOnSecondAspirate(ScriptedPipette):
        def execute(self, command: str, value: str | None = None, timeout: float | None = None) -> str:
            if command == "RI" and any(name == "RI" for name, _value in self.commands):
                self.commands.append((command, None if value is None else str(value)))
                raise SatoriusDeviceError("stopped")
            return super().execute(command=command, value=value, timeout=timeout)

    pipette = StopOnSecondAspirate()
    with pytest.raises(SatoriusDeviceError, match="stopped"):
        pipette.aspirate(1000, 200)
    assert pipette.get_tracked_volume() == pytest.approx(133 * 2.5)
    assert pipette.commands[-1] == ("SI", "3")


def test_full_dispense_paces_the_liquid_and_then_blows_out():
    pipette = ScriptedPipette()
    pipette.aspirate(1000)
    pipette.commands.clear()
    pipette._now = 0.0
    result = pipette.dispense(1000, 200)
    assert _values(pipette, "RO") == ["133", "133", "134"]
    assert [name for name, _value in pipette.commands if name in {"RO", "RB"}][-1] == "RB"
    assert result["blowout"] is True
    assert result["tracked_volume_ul"] == 0


def test_partial_dispense_does_not_blow_out():
    pipette = ScriptedPipette()
    pipette.aspirate(1000)
    result = pipette.dispense(500, 410)
    assert "RB" not in [name for name, _value in pipette.commands]
    assert result["blowout"] is False
    assert result["tracked_volume_ul"] == 500
    assert sum(int(step) for step in _values(pipette, "RO")) == 200


def test_volume_limits_match_the_50_1000_body():
    pipette = ScriptedPipette()
    for amount in (25, 47.5, 51, 1002.5, 0, -50, True):
        with pytest.raises(ValueError):
            pipette.aspirate(amount)
    pipette.aspirate(600)
    with pytest.raises(ValueError, match="capacity"):
        pipette.aspirate(600)
    assert pipette.get_tracked_volume() == 600
    with pytest.raises(ValueError, match="tracked"):
        pipette.dispense(650)
