from qubot.end_effector.rline import RLineModel
from qubot.end_effector.satorius_multistep import SatoriusController


def test_telemetry_skips_the_plunger_when_the_port_is_closed():
    pipette = SatoriusController(
        port_name="unused",
        model=RLineModel.UL_50_1000,
        step_resolution=10,
        response_time_s=1.03,
    )
    reading = pipette.read_telemetry()
    assert reading["plunger_step"] is None
    assert reading["status_code"] is None
    assert reading["tip_attached"] is False
