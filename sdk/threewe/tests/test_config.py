# SPDX-License-Identifier: Apache-2.0
"""Tests for configuration loading."""

from pathlib import Path

from threewe.config import RobotConfig, load_config


class TestLoadConfig:
    def test_default_config_loads(self):
        config = load_config("standard_v2")
        assert config.hardware.platform == "3we_standard_v2"
        assert config.limits.max_linear_velocity == 0.5
        assert config.limits.max_angular_velocity == 1.0
        assert config.navigation.planner == "smac_2d"
        assert config.api.image_size == (640, 480)
        assert config.api.lidar_points == 360

    def test_missing_config_returns_defaults(self):
        config = load_config("nonexistent_config_xyz")
        assert config.hardware.platform == "3we_standard_v2"
        assert config.limits.max_linear_velocity == 0.5

    def test_robot_config_defaults(self):
        config = RobotConfig()
        assert config.hardware.platform == "3we_standard_v2"
        assert config.hardware.wheels == "mecanum_65mm"
        assert config.hardware.lidar == "ld06"
        assert config.hardware.imu == "bno055"
        assert config.limits.safety_distance == 0.15


class TestConfigFile:
    def test_builtin_config_file_exists(self):
        config_path = Path(__file__).parent.parent / "configs" / "standard_v2.yaml"
        assert config_path.is_file()
