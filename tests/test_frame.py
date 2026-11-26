import pytest

from qubot.gantry import Frame


class Recorder:
    def __init__(self):
        self.calls = []

    def set_axis_limits(self, axis, low, high):
        self.calls.append((axis, low, high))


def frame(**overrides):
    values = dict(axes=("X", "Y", "Z"), hardware_limits={"X": (-116, 0), "Y": (-28, 0), "Z": (0, 0)})
    values.update(overrides)
    return Frame(**values)


def test_from_dict_reads_a_contract_table():
    f = Frame.from_dict(
        {
            "axes": ["X", "Y", "Z"],
            "hardware_limits": {"X": [0, 830], "Y": [-280, 0], "Z": [-240, 0]},
            "default_deck": {"rows": 4, "cols": 8},
            "home_order": ["Z", "X", "Y"],
            "required_settings": {"130": 175},
        }
    )
    assert f.hardware_limits["X"] == (0.0, 830.0)
    assert f.home_order == ("Z", "X", "Y")
    assert f.required_settings == {130: 175.0}
    assert len(f.slot_names()) == 32


def test_bad_frames_are_refused():
    with pytest.raises(ValueError):
        frame(axes=("X", "Y"))
    with pytest.raises(ValueError):
        frame(hardware_limits={"X": (1, 0), "Y": (-28, 0), "Z": (0, 0)})
    with pytest.raises(ValueError):
        frame(home_order=("A",))
    with pytest.raises(ValueError):
        Frame.from_dict({"axes": ["X"], "hardware_limits": {"X": [0, 1]}, "limits": {}})


def test_apply_skips_a_zero_travel_axis():
    recorder = Recorder()
    frame().apply_axis_limits(recorder)
    assert recorder.calls == [("X", -116.0, 0.0), ("Y", -28.0, 0.0)]


def test_soft_limits_must_sit_inside_the_frame():
    recorder = Recorder()
    frame().apply_axis_limits(recorder, {"X": (-100, 0)})
    assert recorder.calls == [("X", -100.0, 0.0)]
    with pytest.raises(ValueError):
        frame().apply_axis_limits(recorder, {"X": (-119, 0)})
    with pytest.raises(ValueError):
        frame().apply_axis_limits(recorder, {"A": (0, 1)})
    with pytest.raises(ValueError):
        frame().apply_axis_limits(recorder, {"X": (-5, -5)})
