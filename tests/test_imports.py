"""Short imports from each area resolve to the defining modules, lazily."""

import subprocess
import sys

import qubot.end_effector as end_effector
import qubot.gantry as gantry


def test_gantry_short_names_are_the_module_classes():
    from qubot.gantry import (
        Frame,
        GrblHALController,
        GrblTelnetController,
        GrblWSController,
        RepRapHTTPController,
    )
    from qubot.gantry.frame import Frame as frame_cls
    from qubot.gantry.grbl import GrblHALController as grbl_cls
    from qubot.gantry.grbl_telnet import GrblTelnetController as telnet_cls
    from qubot.gantry.grbl_ws import GrblWSController as ws_cls
    from qubot.gantry.reprap_http import RepRapHTTPController as reprap_cls

    assert (
        Frame,
        GrblHALController,
        GrblTelnetController,
        GrblWSController,
        RepRapHTTPController,
    ) == (
        frame_cls,
        grbl_cls,
        telnet_cls,
        ws_cls,
        reprap_cls,
    )


def test_end_effector_short_names_and_pipette_modules():
    from qubot.end_effector import Capper, Chamber, LedBoard, ParallelFingers, RotatingVacuumGripper
    from qubot.end_effector import rline_50_1000, rline_50_1000_multistep
    from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper as gripper_cls

    assert RotatingVacuumGripper is gripper_cls
    assert rline_50_1000.connect is not rline_50_1000_multistep.connect
    assert {Capper.__name__, Chamber.__name__, LedBoard.__name__, ParallelFingers.__name__} == {
        "Capper",
        "Chamber",
        "LedBoard",
        "ParallelFingers",
    }


def test_every_listed_name_resolves():
    for module in (gantry, end_effector):
        for name in module.__all__:
            assert getattr(module, name) is not None
            assert name in dir(module)


def test_unknown_name_raises_attribute_error():
    import pytest

    with pytest.raises(AttributeError):
        gantry.NoSuchController
    with pytest.raises(AttributeError):
        end_effector.NoSuchEffector


def test_package_imports_do_not_load_serial():
    code = "import sys, qubot, qubot.gantry, qubot.end_effector; print('serial' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
