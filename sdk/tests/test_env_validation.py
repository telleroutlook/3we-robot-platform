# SPDX-License-Identifier: Apache-2.0


import pytest

from payload_interface.env_validation import EnvValidationError, RobotEnv, load_env


class TestRobotEnv:
    def test_defaults_are_valid(self) -> None:
        env = RobotEnv()
        assert env.ros_domain_id == 0
        assert env.robot_target_sku == "standard"

    def test_valid_sku_variants(self) -> None:
        for sku in ("basic", "standard", "pro", "industrial"):
            env = RobotEnv(robot_target_sku=sku)
            assert env.robot_target_sku == sku

    def test_invalid_sku_raises(self) -> None:
        with pytest.raises(EnvValidationError, match="ROBOT_TARGET_SKU"):
            RobotEnv(robot_target_sku="invalid")

    def test_ros_domain_id_boundary(self) -> None:
        RobotEnv(ros_domain_id=0)
        RobotEnv(ros_domain_id=232)

        with pytest.raises(EnvValidationError, match="ROS_DOMAIN_ID"):
            RobotEnv(ros_domain_id=233)

        with pytest.raises(EnvValidationError, match="ROS_DOMAIN_ID"):
            RobotEnv(ros_domain_id=-1)

    def test_invalid_mqtt_protocol(self) -> None:
        with pytest.raises(EnvValidationError, match="MQTT_BROKER_URL"):
            RobotEnv(mqtt_broker_url="http://localhost:1883")

    def test_valid_mqtt_protocols(self) -> None:
        RobotEnv(mqtt_broker_url="mqtt://localhost:1883")
        RobotEnv(mqtt_broker_url="mqtts://broker.example.com:8883")

    def test_empty_mqtt_is_valid(self) -> None:
        RobotEnv(mqtt_broker_url="")


class TestLoadEnv:
    def test_load_with_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ROS_DOMAIN_ID", raising=False)
        monkeypatch.delenv("ROBOT_TARGET_SKU", raising=False)
        env = load_env()
        assert env.ros_domain_id == 0
        assert env.robot_target_sku == "standard"

    def test_load_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ROS_DOMAIN_ID", "42")
        monkeypatch.setenv("ROBOT_TARGET_SKU", "pro")
        monkeypatch.setenv("MQTT_BROKER_URL", "mqtts://fleet.example.com:8883")

        env = load_env()
        assert env.ros_domain_id == 42
        assert env.robot_target_sku == "pro"
        assert env.mqtt_broker_url == "mqtts://fleet.example.com:8883"

    def test_load_invalid_domain_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ROS_DOMAIN_ID", "not_a_number")
        with pytest.raises(EnvValidationError, match="must be an integer"):
            load_env()
