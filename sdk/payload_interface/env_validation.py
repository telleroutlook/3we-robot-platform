# SPDX-License-Identifier: Apache-2.0
"""
Runtime environment variable validation for the robot platform SDK.

Validates required environment variables at startup and provides
typed access with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class EnvValidationError(Exception):
    """Raised when required environment variables are missing or invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        msg = "Environment validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(msg)


@dataclass(frozen=True)
class RobotEnv:
    """Validated environment configuration for the robot platform."""

    ros_domain_id: int = 0
    rmw_implementation: str = "rmw_fastrtps_cpp"
    microros_agent_dev: str = "/dev/ttyUSB0"
    mqtt_broker_url: str = "mqtt://localhost:1883"
    mqtt_fleet_topic_prefix: str = "fleet/"
    robot_id: str = ""
    robot_target_sku: str = "standard"

    _valid_skus: tuple[str, ...] = field(
        default=("basic", "standard", "pro", "industrial"),
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        errors: list[str] = []

        if not 0 <= self.ros_domain_id <= 232:
            errors.append(f"ROS_DOMAIN_ID must be 0-232, got {self.ros_domain_id}")

        if self.robot_target_sku not in self._valid_skus:
            errors.append(
                f"ROBOT_TARGET_SKU must be one of {self._valid_skus}, got '{self.robot_target_sku}'"
            )

        if self.mqtt_broker_url and not self.mqtt_broker_url.startswith(
            ("mqtt://", "mqtts://")
        ):
            errors.append("MQTT_BROKER_URL must use mqtt:// or mqtts:// protocol")

        if errors:
            raise EnvValidationError(errors)


def load_env() -> RobotEnv:
    """Load and validate environment variables. Raises EnvValidationError on failure."""
    ros_domain_raw = os.environ.get("ROS_DOMAIN_ID", "0")

    try:
        ros_domain_id = int(ros_domain_raw)
    except ValueError:
        raise EnvValidationError(
            [f"ROS_DOMAIN_ID must be an integer, got '{ros_domain_raw}'"]
        )

    return RobotEnv(
        ros_domain_id=ros_domain_id,
        rmw_implementation=os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp"),
        microros_agent_dev=os.environ.get("MICROROS_AGENT_DEV", "/dev/ttyUSB0"),
        mqtt_broker_url=os.environ.get("MQTT_BROKER_URL", "mqtt://localhost:1883"),
        mqtt_fleet_topic_prefix=os.environ.get("MQTT_FLEET_TOPIC_PREFIX", "fleet/"),
        robot_id=os.environ.get("ROBOT_ID", ""),
        robot_target_sku=os.environ.get("ROBOT_TARGET_SKU", "standard"),
    )
