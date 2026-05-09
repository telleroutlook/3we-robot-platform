# SPDX-License-Identifier: Apache-2.0
"""Validates simulation configuration files, world files, and Gazebo Xacro overlay."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

PKG_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PKG_DIR / "config"
WORLDS_DIR = PKG_DIR / "worlds"
URDF_DIR = PKG_DIR / "urdf"


@pytest.fixture(scope="module")
def bridge_params() -> list:
    with open(CONFIG_DIR / "bridge_params.yaml") as f:
        return yaml.safe_load(f)


class TestBridgeParams:
    """Validate ros_gz_bridge topic configuration."""

    def test_parsable(self, bridge_params: list) -> None:
        assert bridge_params is not None
        assert isinstance(bridge_params, list)
        assert len(bridge_params) > 0

    def test_topics_complete(self, bridge_params: list) -> None:
        ros_topics = [entry["ros_topic_name"] for entry in bridge_params]
        required = [
            "/cmd_vel",
            "/odom",
            "/imu/data",
            "/clock",
            "/joint_states",
            "/ultrasonic/front",
            "/ultrasonic/back",
            "/ultrasonic/left",
            "/ultrasonic/right",
        ]
        for topic in required:
            assert topic in ros_topics, f"Missing bridge topic: {topic}"

    def test_cmd_vel_bidirectional(self, bridge_params: list) -> None:
        cmd_vel = next(e for e in bridge_params if e["ros_topic_name"] == "/cmd_vel")
        assert cmd_vel["direction"] == "BIDIRECTIONAL"

    def test_sensor_topics_gz_to_ros(self, bridge_params: list) -> None:
        sensor_topics = ["/odom", "/imu/data", "/ultrasonic/front", "/clock"]
        for topic_name in sensor_topics:
            entry = next(e for e in bridge_params if e["ros_topic_name"] == topic_name)
            assert entry["direction"] == "GZ_TO_ROS", (
                f"{topic_name} should be GZ_TO_ROS"
            )

    def test_all_entries_have_types(self, bridge_params: list) -> None:
        for entry in bridge_params:
            assert "ros_type_name" in entry
            assert "gz_type_name" in entry


class TestWorldFiles:
    """Validate Gazebo world files are well-formed XML/SDF."""

    @pytest.mark.parametrize("world_file", ["empty.sdf", "obstacles.sdf"])
    def test_world_valid_xml(self, world_file: str) -> None:
        path = WORLDS_DIR / world_file
        assert path.exists(), f"World file missing: {world_file}"
        tree = ET.parse(str(path))
        root = tree.getroot()
        assert root.tag == "sdf"

    def test_obstacles_world_has_models(self) -> None:
        tree = ET.parse(str(WORLDS_DIR / "obstacles.sdf"))
        root = tree.getroot()
        world = root.find("world")
        assert world is not None
        models = world.findall("model")
        assert len(models) >= 1, "Obstacles world should have at least one model"


class TestGazeboXacro:
    """Validate the Gazebo-specific URDF overlay."""

    @pytest.fixture(scope="class")
    def gazebo_urdf_xml(self) -> str:
        try:
            import xacro
        except ImportError:
            pytest.skip("xacro package not available")

        xacro_file = URDF_DIR / "robot_gazebo.urdf.xacro"
        assert xacro_file.exists()
        doc = xacro.process_file(str(xacro_file))
        return doc.toprettyxml(indent="  ")

    def test_processable(self, gazebo_urdf_xml: str) -> None:
        assert len(gazebo_urdf_xml) > 0
        root = ET.fromstring(gazebo_urdf_xml)
        assert root.tag == "robot"

    def test_has_gazebo_plugins(self, gazebo_urdf_xml: str) -> None:
        assert "imu_sensor" in gazebo_urdf_xml or "imu" in gazebo_urdf_xml.lower()

    def test_has_ultrasonic_sensors(self, gazebo_urdf_xml: str) -> None:
        assert "ultrasonic_front" in gazebo_urdf_xml
        assert "ultrasonic_back" in gazebo_urdf_xml
        assert "ultrasonic_left" in gazebo_urdf_xml
        assert "ultrasonic_right" in gazebo_urdf_xml
