# SPDX-License-Identifier: Apache-2.0
"""Tests for the Hardware Abstraction Layer."""

from __future__ import annotations

import pytest

from threewe.hal.interface import (
    HardwareProfile,
    HardwareProfileData,
    load_hardware_profile,
)


class TestHardwareProfileData:
    def test_default_profile(self):
        profile = HardwareProfileData()
        assert profile.name == "3we_standard_v2"
        assert profile.wheel_type == "mecanum"
        assert profile.wheel_separation == 0.24
        assert profile.max_linear_velocity == 0.5
        assert len(profile.sensors) == 4

    def test_satisfies_protocol(self):
        profile = HardwareProfileData()
        assert isinstance(profile, HardwareProfile)


class TestLoadHardwareProfile:
    def test_load_default(self):
        profile = load_hardware_profile("3we_standard_v2")
        assert profile.name == "3we_standard_v2"
        assert profile.wheel_type == "mecanum"

    def test_load_agilex_scout(self):
        profile = load_hardware_profile("agilex_scout")
        assert profile.name == "agilex_scout"
        assert profile.wheel_type == "differential"
        assert profile.max_linear_velocity == 1.5
        assert profile.weight_kg == 65.0

    def test_load_turtlebot4(self):
        profile = load_hardware_profile("turtlebot4")
        assert profile.name == "turtlebot4"
        assert profile.wheel_type == "differential"
        assert profile.max_linear_velocity == 0.31

    def test_load_unitree_go2(self):
        profile = load_hardware_profile("unitree_go2")
        assert profile.name == "unitree_go2"
        assert profile.wheel_type == "legged"
        assert profile.max_linear_velocity == 2.5

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown hardware profile"):
            load_hardware_profile("nonexistent_robot")

    def test_load_from_yaml(self, tmp_path):
        yaml = pytest.importorskip("yaml")

        config = {
            "name": "custom_bot",
            "wheel_type": "omni",
            "wheel_separation": 0.35,
            "wheel_radius": 0.06,
            "max_linear_velocity": 1.0,
            "max_angular_velocity": 3.0,
            "sensors": ["lidar_custom", "camera_custom"],
            "weight_kg": 8.0,
        }
        path = tmp_path / "custom_bot.yaml"
        path.write_text(yaml.dump(config))

        profile = load_hardware_profile(str(path))
        assert profile.name == "custom_bot"
        assert profile.wheel_type == "omni"
        assert profile.wheel_separation == 0.35
        assert len(profile.sensors) == 2


class TestRobotHardwareParam:
    def test_robot_accepts_hardware_param(self):
        from threewe.robot import Robot

        robot = Robot(backend="gazebo", hardware="agilex_scout", auto_connect=False)
        assert robot.hardware.name == "agilex_scout"
        assert robot.hardware.max_linear_velocity == 1.5

    def test_robot_default_hardware(self):
        from threewe.robot import Robot

        robot = Robot(backend="gazebo", auto_connect=False)
        assert robot.hardware.name == "3we_standard_v2"
