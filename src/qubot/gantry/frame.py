"""Frame facts for one gantry, configured by the edge that drives it.

qubot ships no machine values. An edge constructs its frame in its own code::

    from qubot.gantry import Frame

    FRAME = Frame(axes=("X", "Y", "Z"), hardware_limits={"X": (0, 830), ...})
    FRAME.apply_axis_limits(controller, SOFT_LIMITS)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

Limits = Mapping[str, tuple[float, float]]


@dataclass(frozen=True)
class Frame:
    """Hardware travel, axes, and default deck of one physical gantry.

    ``hardware_limits`` is frame travel per axis in mm, ``(low, high)``.
    ``home_order``, ``expected_identity``, and ``required_settings`` are optional
    firmware facts the edge may check before moving.
    """

    axes: tuple[str, ...]
    hardware_limits: dict[str, tuple[float, float]]
    default_deck: dict[str, int] = field(default_factory=lambda: {"rows": 2, "cols": 2})
    home_order: Optional[tuple[str, ...]] = None
    expected_identity: Optional[str] = None
    required_settings: dict[int, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        axes = tuple(str(axis) for axis in self.axes)
        limits = {str(axis): (float(low), float(high)) for axis, (low, high) in self.hardware_limits.items()}
        if set(limits) != set(axes):
            raise ValueError(f"hardware_limits axes {sorted(limits)} do not match axes {list(axes)}")
        for axis, (low, high) in limits.items():
            if low > high:
                raise ValueError(f"{axis} hardware limits {(low, high)} have low above high")
        deck = {"rows": int(self.default_deck["rows"]), "cols": int(self.default_deck["cols"])}
        if deck["rows"] < 1 or deck["cols"] < 1:
            raise ValueError(f"default_deck must have at least one row and column, got {deck}")
        if self.home_order is not None:
            order = tuple(str(axis) for axis in self.home_order)
            unknown = [axis for axis in order if axis not in limits]
            if unknown:
                raise ValueError(f"home_order names axes not on this frame: {unknown}")
            object.__setattr__(self, "home_order", order)
        object.__setattr__(self, "axes", axes)
        object.__setattr__(self, "hardware_limits", limits)
        object.__setattr__(self, "default_deck", deck)
        object.__setattr__(
            self,
            "required_settings",
            {int(key): float(value) for key, value in self.required_settings.items()},
        )

    def check_limits(self, limits: Optional[Limits] = None) -> dict[str, tuple[float, float]]:
        """Return limits that sit inside this frame. None returns the hardware limits.

        Raises:
            ValueError: If an axis is not on the frame or a bound is outside it.
        """
        if limits is None:
            return dict(self.hardware_limits)
        checked: dict[str, tuple[float, float]] = {}
        for axis, bounds in limits.items():
            if axis not in self.hardware_limits:
                raise ValueError(f"Axis {axis} is not on this frame")
            low, high = (float(bound) for bound in bounds)
            hard_low, hard_high = self.hardware_limits[axis]
            if low < hard_low or high > hard_high or low > high:
                raise ValueError(f"{axis} limits {tuple(bounds)} are outside the frame {(hard_low, hard_high)}")
            checked[axis] = (low, high)
        return checked

    def apply_axis_limits(self, controller, limits: Optional[Limits] = None) -> None:
        """Push limits inside this frame to the controller. None uses the hardware limits.

        An axis with no travel (low equal to high) is not pushed; transports refuse
        a zero-length window and an unset axis already has none. A zero-length soft
        window on an axis that does have travel is refused.
        """
        for axis, (low, high) in self.check_limits(limits).items():
            if low == high:
                if (low, high) != self.hardware_limits[axis]:
                    raise ValueError(
                        f"{axis} limits {(low, high)} have no travel inside the frame {self.hardware_limits[axis]}"
                    )
                continue
            controller.set_axis_limits(axis, low, high)

    def slot_names(self, rows: Optional[int] = None, cols: Optional[int] = None) -> list[str]:
        """Deck slot names, ``A1`` upward. Defaults to the frame's default deck."""
        rows = self.default_deck["rows"] if rows is None else rows
        cols = self.default_deck["cols"] if cols is None else cols
        return [f"{chr(65 + row)}{col + 1}" for row in range(rows) for col in range(cols)]


__all__ = ["Frame"]
