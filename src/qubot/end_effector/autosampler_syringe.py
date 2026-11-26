"""Passive syringe. No bus and no port. Liquid handling stays on the separate pump edge.

`syringe_length_mm` for the current IMRE holder is 50 mm. That figure is the syringe plus the vial holder, not the needle alone. With that holder, travel past Z = -125 was observed to knock the needle into the base of the mounted vial holder. This is a clearance observation. It is not an axis limit. The gantry keeps its firmware Z range. Remeasure the 50 mm if the vial holder changes.
"""

AXIS = ""
COMMUNICATION = "none"
PORT_ENV = ""


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


__all__ = ["AXIS", "COMMUNICATION", "PORT_ENV", "narrow_z"]
