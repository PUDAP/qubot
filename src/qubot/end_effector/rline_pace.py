"""Apparent aspirate and dispense speed for a pipette that only has presets.

The rLine plunger has six fixed speeds. A requested speed that is not one of
them is made from a faster preset, split into several moves. ``step_resolution``
and ``response_time_s`` are manual calibrations: the smallest step count whose
volume error is still tolerable, and the seconds one command round-trip is
assumed to take. Both are measured per pipette and passed in by the edge.

The plan picks the feasible preset with the smallest area between the requested
ramp and that preset. Each interval then lasts ``steps * uL_per_step / preset``
plus an equal share of the extra time ``volume * (1/speed - 1/preset)``. The
sum is ``volume / speed`` seconds.
"""

from __future__ import annotations

def interpolate_speed(
    volume: float,
    speed: float,
    *,
    speed_presets: tuple[float, ...],
    volume_resolution: float,
    step_resolution: int,
    time_resolution: float,
) -> dict[str, float | int]:
    """Return the preset, interval count, step size, and per-interval pause.

    A return with ``n_intervals`` of 0 means the request cannot be paced.
    ``preset_speed`` is then the slowest preset and the step fields are 0.
    """
    total_steps = volume / volume_resolution
    if total_steps < step_resolution:
        return {
            "preset_speed": speed_presets[0],
            "n_intervals": 0,
            "step_size": 0,
            "delay": 0,
        }

    if speed in speed_presets:
        return {
            "preset_speed": speed,
            "n_intervals": 1,
            "step_size": total_steps,
            "delay": 0,
        }

    deviations: dict[float, dict[str, float | int]] = {}
    for preset in speed_presets:
        if preset < speed:
            continue
        total_delay = volume * (1 / speed - 1 / preset)
        if total_delay < time_resolution:
            continue
        n_intervals = int(max(1, min(total_steps / step_resolution, total_delay / time_resolution)))
        steps_per_interval = int(total_steps / n_intervals)
        delay_per_interval = total_delay / n_intervals
        area = (
            0.5
            * (volume**2)
            * (1 / volume_resolution)
            * (1 / n_intervals)
            * (1 / speed - 1 / preset)
        )
        deviations[area] = {
            "preset_speed": preset,
            "n_intervals": n_intervals,
            "step_size": steps_per_interval,
            "delay": delay_per_interval,
        }
    if not deviations:
        return {
            "preset_speed": speed_presets[0],
            "n_intervals": 0,
            "step_size": 0,
            "delay": 0,
        }
    return deviations[min(deviations)]


def interval_steps(total_steps: int, n_intervals: int, step_size: int) -> list[int]:
    """Split ``total_steps`` the way the aspirate loop does.

    Every interval except the last uses ``step_size``. The last interval takes
    whatever steps remain, so the volume is not shortened by integer division.
    """
    if n_intervals < 1:
        raise ValueError("n_intervals must be positive")
    remaining = total_steps
    steps: list[int] = []
    for index in range(n_intervals):
        step = step_size if index + 1 != n_intervals else remaining
        if step < 1:
            raise ValueError(
                f"Interval {index + 1} of {n_intervals} would move {step} steps"
            )
        steps.append(int(step))
        remaining -= step
    if remaining != 0:
        raise ValueError(f"Steps {steps} do not add up to {total_steps}")
    return steps


def plan_transfer(
    volume_ul: float,
    speed_ul_s: float,
    *,
    microliters_per_step: float,
    speed_presets: tuple[int, ...] | tuple[float, ...],
    step_resolution: int,
    response_time_s: float,
) -> dict:
    """Build a runnable plan or raise if this calibration cannot hit the speed."""
    if isinstance(speed_ul_s, bool) or not isinstance(speed_ul_s, (int, float)) or speed_ul_s <= 0:
        raise ValueError(f"speed_ul_s must be positive microliters per second, got {speed_ul_s!r}")
    if microliters_per_step <= 0:
        raise ValueError("microliters_per_step must be positive")
    if isinstance(step_resolution, bool) or not isinstance(step_resolution, int) or step_resolution < 1:
        raise ValueError("step_resolution must be a positive integer")
    if (
        isinstance(response_time_s, bool)
        or not isinstance(response_time_s, (int, float))
        or response_time_s <= 0
    ):
        raise ValueError("response_time_s must be positive")

    total_steps = volume_ul / microliters_per_step
    if abs(total_steps - round(total_steps)) > 1e-6:
        raise ValueError(
            f"{volume_ul} uL is not a whole number of {microliters_per_step} uL steps"
        )
    total_steps = int(round(total_steps))
    if total_steps < step_resolution:
        raise ValueError(
            f"{volume_ul} uL is {total_steps} steps, below the calibrated "
            f"step_resolution of {step_resolution} steps "
            f"({step_resolution * microliters_per_step:g} uL)"
        )

    presets = tuple(speed_presets)
    raw = interpolate_speed(
        volume_ul,
        speed_ul_s,
        speed_presets=presets,
        volume_resolution=microliters_per_step,
        step_resolution=step_resolution,
        time_resolution=float(response_time_s),
    )
    if int(raw["n_intervals"]) <= 0:
        raise ValueError(
            f"No multistep plan reaches {speed_ul_s:g} uL/s for {volume_ul:g} uL "
            f"with response_time_s {response_time_s:g}. Preset speeds are "
            f"{presets} uL/s, and nothing faster than {presets[-1]:g} uL/s is possible."
        )
    steps = interval_steps(total_steps, int(raw["n_intervals"]), int(raw["step_size"]))
    if any(step < 2 for step in steps):
        raise ValueError(
            f"The plan for {volume_ul:g} uL at {speed_ul_s:g} uL/s includes a move "
            "shorter than the 2-step minimum"
        )
    return {
        "preset_speed": raw["preset_speed"],
        "n_intervals": int(raw["n_intervals"]),
        "step_size": int(raw["step_size"]),
        "delay": float(raw["delay"]),
        "total_steps": total_steps,
        "steps": steps,
        "volume_ul": volume_ul,
        "speed_ul_s": speed_ul_s,
    }


def remaining_pause(elapsed_s: float, move_time_s: float, interval_delay_s: float) -> float:
    """Seconds still to wait so one interval lasts the move plus its pause.

    ``elapsed_s`` is the time already spent sending the command and waiting
    until the drive is idle. The command round-trip is part of the interval,
    not an extra delay on top of it.
    """
    return max(0.0, move_time_s + interval_delay_s - elapsed_s)
