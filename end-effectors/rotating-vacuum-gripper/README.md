# rotating-vacuum-gripper

Vacuum cup and yaw servo for the claw. Both ride the gantry GRBL port. There is no second port.

Yaw is `C`, limited to −180° through 0°. Calibrated servo pulses are 0° → `S14`, −90° → `S124`, −180° → `S244`. Intermediate angles are linear between those points. The older expression for an in-between angle omits the calibrated endpoint and yields a negative pulse; this package does not send that value.

Vacuum on is `M8`. Vacuum off is `M9`. The delays are 3 s on and 3 s off. Rotation is refused when robot-frame Z is below −5 mm. Emergency stop of the gantry does not vent the cup.
