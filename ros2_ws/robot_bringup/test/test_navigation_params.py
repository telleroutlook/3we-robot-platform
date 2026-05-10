# SPDX-License-Identifier: Apache-2.0
"""Validates Nav2, SLAM, and QoS configuration files are well-formed and consistent."""

from pathlib import Path

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture(scope="module")
def nav2_params() -> dict:
    with open(CONFIG_DIR / "nav2_params.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def slam_params() -> dict:
    with open(CONFIG_DIR / "slam_params.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def qos_profiles() -> dict:
    with open(CONFIG_DIR / "qos_profiles.yaml") as f:
        return yaml.safe_load(f)


class TestNav2Params:
    """Validate Nav2 parameter structure and mecanum-specific settings."""

    def test_parsable(self, nav2_params: dict) -> None:
        assert nav2_params is not None
        assert isinstance(nav2_params, dict)

    def test_required_sections(self, nav2_params: dict) -> None:
        required = [
            "bt_navigator",
            "controller_server",
            "planner_server",
            "local_costmap",
            "global_costmap",
            "behavior_server",
        ]
        for section in required:
            assert section in nav2_params, f"Missing section: {section}"

    def test_mecanum_lateral_velocity_enabled(self, nav2_params: dict) -> None:
        follow_path = nav2_params["controller_server"]["ros__parameters"]["FollowPath"]
        assert follow_path["min_vel_y"] < 0, "Mecanum requires negative min_vel_y"
        assert follow_path["max_vel_y"] > 0, "Mecanum requires positive max_vel_y"

    def test_robot_radius_consistent(self, nav2_params: dict) -> None:
        local_radius = nav2_params["local_costmap"]["local_costmap"]["ros__parameters"][
            "robot_radius"
        ]
        global_radius = nav2_params["global_costmap"]["global_costmap"][
            "ros__parameters"
        ]["robot_radius"]
        assert local_radius == global_radius

    def test_controller_frequency_positive(self, nav2_params: dict) -> None:
        freq = nav2_params["controller_server"]["ros__parameters"][
            "controller_frequency"
        ]
        assert freq > 0


class TestSlamParams:
    """Validate SLAM toolbox parameter structure."""

    def test_parsable(self, slam_params: dict) -> None:
        assert slam_params is not None
        assert "slam_toolbox" in slam_params

    def test_required_keys(self, slam_params: dict) -> None:
        params = slam_params["slam_toolbox"]["ros__parameters"]
        required = ["resolution", "odom_frame", "base_frame", "mode"]
        for key in required:
            assert key in params, f"Missing SLAM key: {key}"

    def test_resolution_reasonable(self, slam_params: dict) -> None:
        resolution = slam_params["slam_toolbox"]["ros__parameters"]["resolution"]
        assert 0.01 <= resolution <= 0.2

    def test_mode_is_mapping(self, slam_params: dict) -> None:
        mode = slam_params["slam_toolbox"]["ros__parameters"]["mode"]
        assert mode in ("mapping", "localization")


class TestQosProfiles:
    """Validate QoS profile configuration."""

    def test_parsable(self, qos_profiles: dict) -> None:
        assert qos_profiles is not None
        assert "qos_profiles" in qos_profiles

    def test_emergency_stop_reliable(self, qos_profiles: dict) -> None:
        estop = qos_profiles["qos_profiles"]["emergency_stop"]
        assert estop["reliability"] == "reliable"
        assert estop["durability"] == "transient_local"

    def test_cmd_vel_reliable(self, qos_profiles: dict) -> None:
        cmd_vel = qos_profiles["qos_profiles"]["cmd_vel"]
        assert cmd_vel["reliability"] == "reliable"

    def test_sensor_topics_best_effort(self, qos_profiles: dict) -> None:
        profiles = qos_profiles["qos_profiles"]
        for topic in ["odom", "ultrasonic", "imu"]:
            assert profiles[topic]["reliability"] == "best_effort"

    def test_topic_qos_map_exists(self, qos_profiles: dict) -> None:
        assert "topic_qos_map" in qos_profiles
        mapping = qos_profiles["topic_qos_map"]
        assert "/cmd_vel" in mapping
        assert "/emergency_stop" in mapping


class TestNav2ParamsIndustrial:
    """Validate Industrial SKU Nav2 parameters (500x400mm chassis, 97mm wheels)."""

    @pytest.fixture(scope="class")
    def nav2_industrial(self) -> dict:
        industrial_file = CONFIG_DIR / "nav2_params_industrial.yaml"
        if not industrial_file.exists():
            pytest.skip("Industrial nav2 params file not found")
        with open(industrial_file) as f:
            return yaml.safe_load(f)

    def test_parsable(self, nav2_industrial: dict) -> None:
        assert nav2_industrial is not None
        assert isinstance(nav2_industrial, dict)

    def test_required_sections(self, nav2_industrial: dict) -> None:
        required = [
            "bt_navigator",
            "controller_server",
            "planner_server",
            "local_costmap",
            "global_costmap",
            "behavior_server",
        ]
        for section in required:
            assert section in nav2_industrial, f"Missing section: {section}"

    def test_robot_radius_reflects_larger_chassis(self, nav2_industrial: dict) -> None:
        local_r = nav2_industrial["local_costmap"]["local_costmap"]["ros__parameters"][
            "robot_radius"
        ]
        assert local_r >= 0.30, (
            f"Industrial robot_radius {local_r} too small for 500x400 chassis"
        )

    def test_robot_radius_consistent(self, nav2_industrial: dict) -> None:
        local_r = nav2_industrial["local_costmap"]["local_costmap"]["ros__parameters"][
            "robot_radius"
        ]
        global_r = nav2_industrial["global_costmap"]["global_costmap"][
            "ros__parameters"
        ]["robot_radius"]
        assert local_r == global_r

    def test_mecanum_lateral_velocity_enabled(self, nav2_industrial: dict) -> None:
        fp = nav2_industrial["controller_server"]["ros__parameters"]["FollowPath"]
        assert fp["min_vel_y"] < 0, "Mecanum requires negative min_vel_y"
        assert fp["max_vel_y"] > 0, "Mecanum requires positive max_vel_y"

    def test_max_velocity_higher_than_standard(self, nav2_industrial: dict) -> None:
        fp = nav2_industrial["controller_server"]["ros__parameters"]["FollowPath"]
        assert fp["max_vel_x"] >= 0.45, "Industrial should have higher max velocity"
