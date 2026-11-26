"""Passive syringe. No bus and no port. Liquid handling stays on the separate pump edge.

``syringe_length_mm`` is measured per machine and set in the edge's own config. It is
the syringe plus whatever holder it clears, and it narrows downward Z travel. It
is a clearance figure, not an axis limit; the gantry keeps its firmware Z range.
"""

COMMUNICATION = "none"


def narrow_z(z_limits: tuple[float, float], syringe_length_mm: float) -> tuple[float, float]:
    """Shorten downward Z travel by the syringe length. Zero leaves the frame interval unchanged."""
    low, high = z_limits
    length = float(syringe_length_mm)
    if length < 0:
        raise ValueError("syringe_length_mm must be zero or positive")
    narrowed_low = low + length
    if narrowed_low > high:
        raise ValueError("syringe length removes the whole Z range")
    return (narrowed_low, high)


__all__ = ["COMMUNICATION", "narrow_z"]
