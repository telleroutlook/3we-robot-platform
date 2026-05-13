# SPDX-License-Identifier: Apache-2.0
"""Tests for HAL plugin discovery."""

from __future__ import annotations

from pathlib import Path

import yaml

from threewe.hal.discovery import discover_external_profiles, list_all_profiles
from threewe.hal.interface import HardwareProfileData, load_hardware_profile


class TestListAllProfiles:
    def test_includes_builtins(self):
        profiles = list_all_profiles()
        assert "3we_standard_v2" in profiles
        assert "agilex_scout" in profiles
        assert "turtlebot4" in profiles
        assert "unitree_go2" in profiles
        assert len(profiles) >= 4

    def test_profile_types(self):
        profiles = list_all_profiles()
        for profile in profiles.values():
            assert isinstance(profile, HardwareProfileData)


class TestDiscoverExternalProfiles:
    def test_returns_empty_when_no_dir(self, monkeypatch):
        monkeypatch.setattr(
            "threewe.hal.discovery._EXTERNAL_PROFILES_DIR",
            Path("/nonexistent/path"),
        )
        profiles = discover_external_profiles()
        assert profiles == {}

    def test_discovers_yaml_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "threewe.hal.discovery._EXTERNAL_PROFILES_DIR",
            tmp_path,
        )
        profile_data = {
            "name": "custom_robot",
            "wheel_type": "omni",
            "wheel_separation": 0.3,
            "wheel_radius": 0.06,
            "max_linear_velocity": 1.0,
            "max_angular_velocity": 3.0,
            "sensors": ["lidar_custom"],
            "weight_kg": 8.0,
        }
        (tmp_path / "custom_robot.yaml").write_text(yaml.dump(profile_data))

        profiles = discover_external_profiles()
        assert "custom_robot" in profiles
        assert profiles["custom_robot"].wheel_type == "omni"
        assert profiles["custom_robot"].max_linear_velocity == 1.0

    def test_ignores_invalid_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "threewe.hal.discovery._EXTERNAL_PROFILES_DIR",
            tmp_path,
        )
        (tmp_path / "broken.yaml").write_text("{{invalid yaml content")
        profiles = discover_external_profiles()
        assert profiles == {}

    def test_external_overrides_builtin(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "threewe.hal.discovery._EXTERNAL_PROFILES_DIR",
            tmp_path,
        )
        profile_data = {
            "name": "3we_standard_v2",
            "wheel_type": "differential",
            "wheel_separation": 0.5,
            "wheel_radius": 0.1,
            "max_linear_velocity": 2.0,
            "max_angular_velocity": 5.0,
            "sensors": ["custom_lidar"],
            "weight_kg": 10.0,
        }
        (tmp_path / "override.yaml").write_text(yaml.dump(profile_data))

        all_profiles = list_all_profiles()
        assert all_profiles["3we_standard_v2"].max_linear_velocity == 2.0


class TestLoadHardwareProfileWithDiscovery:
    def test_loads_external_profile(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "threewe.hal.discovery._EXTERNAL_PROFILES_DIR",
            tmp_path,
        )
        profile_data = {
            "name": "my_robot",
            "wheel_type": "tracked",
            "wheel_separation": 0.4,
            "wheel_radius": 0.08,
            "max_linear_velocity": 0.8,
            "max_angular_velocity": 1.5,
            "sensors": ["camera_front"],
            "weight_kg": 12.0,
        }
        (tmp_path / "my_robot.yaml").write_text(yaml.dump(profile_data))

        profile = load_hardware_profile("my_robot")
        assert profile.name == "my_robot"
        assert profile.wheel_type == "tracked"
