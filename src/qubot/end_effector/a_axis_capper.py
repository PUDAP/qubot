"""Capping toolhead driven by a gantry axis. No bus and no port of its own.

The edge configures the axis, tool length, and mount offset for its machine::

    capper = Capper(axis="A", tool_length_mm=..., mount_offset_x_mm=...)
"""

from dataclasses import dataclass

COMMUNICATION = "gantry"


@dataclass(frozen=True)
class Capper:
    """Where the capper sits on its gantry."""

    axis: str
    tool_length_mm: float
    mount_offset_x_mm: float

    def __post_init__(self) -> None:
        if not str(self.axis).strip():
            raise ValueError("capper axis is empty")
        if self.tool_length_mm < 0:
            raise ValueError(f"tool_length_mm must be zero or positive, got {self.tool_length_mm}")


__all__ = ["COMMUNICATION", "Capper"]
