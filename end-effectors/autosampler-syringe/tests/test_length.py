def test_current_holder_clearance_is_syringe_plus_holder():
    """50 mm is syringe plus the current vial holder, from firmware Z -175 to the observed knock at -125."""
    firmware_z_min = -175.0
    observed_knock_z = -125.0
    syringe_plus_holder_mm = observed_knock_z - firmware_z_min
    assert syringe_plus_holder_mm == 50.0
