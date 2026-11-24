# parallel-force-actuator

Four force actuators, channels 0–3, each on its own serial port at 115200 baud. Port placeholders are `FINGER_1_PORT` through `FINGER_4_PORT`. The stream line is:

```text
{target},{speed},{displacement},{end_stop},{value}\r\n
```

Home writes `H 0`, waits until the reported displacement is −1.0 mm, disconnects, reconnects, and writes `H 0` again. A move writes `G {mm} {rpm}` with `rpm = int(speed_mm_s * steps_per_second)`. `steps_per_second` is 6400, the actuator default. The pescador YAML does not set it.

Travel is −30 mm to 0 mm. Correction is `(raw − b) / a` per channel. Force in newtons is `(corrected − baseline) / 573.2622826433104 × 9.81`.

The configured touch thresholds are 30000 in pescador2 and 7500 in the demo. Those are not plausible newtons. Force-threshold stops stay disabled until the edge contract sets `force_threshold_units` to something other than `ASK`. No finger stop command is known, so a gantry emergency stop does not stop these actuators.
