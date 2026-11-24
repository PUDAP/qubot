# orion-4ch-led

Four LED channels on one serial port, 9600 baud, timeout 1 s. Axis is none. Port placeholder `LED_PORT`.

One write sets every channel:

```text
{p0};{p1};{p2};{p3}\n
```

Off is `0;0;0;0\n`. The reply format is not known, so this package writes the line and does not wait for `ok`. A `force_threshold` value appears on one lamp config and is not used.
