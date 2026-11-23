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
