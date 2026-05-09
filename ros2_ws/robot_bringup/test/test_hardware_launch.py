# SPDX-License-Identifier: Apache-2.0
"""Validates hardware launch file structure and argument declarations."""

import sys
from pathlib import Path

import pytest

LAUNCH_DIR = Path(__file__).resolve().parent.parent / "launch"


@pytest.fixture(scope="module")
def hardware_launch_module():
    """Import hardware.launch.py as a module."""
    sys.path.insert(0, str(LAUNCH_DIR))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hardware_launch", LAUNCH_DIR / "hardware.launch.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except ImportError:
        pytest.skip("launch_ros not available in test environment")
    finally:
        sys.path.pop(0)


def test_launch_description_constructible(hardware_launch_module) -> None:
    from launch import LaunchDescription

    ld = hardware_launch_module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)


def test_declared_arguments(hardware_launch_module) -> None:
    from launch.actions import DeclareLaunchArgument

    ld = hardware_launch_module.generate_launch_description()
    args = [e for e in ld.entities if isinstance(e, DeclareLaunchArgument)]
    arg_names = [a.name for a in args]
    assert "serial_port" in arg_names
    assert "baud_rate" in arg_names


def test_argument_defaults(hardware_launch_module) -> None:
    from launch.actions import DeclareLaunchArgument

    ld = hardware_launch_module.generate_launch_description()
    args = {a.name: a for a in ld.entities if isinstance(a, DeclareLaunchArgument)}
    assert args["serial_port"].default_value is not None
    assert args["baud_rate"].default_value is not None
