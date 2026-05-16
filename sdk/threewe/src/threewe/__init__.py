# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 telleroutlook (https://github.com/telleroutlook/3we-robot-platform)
"""threewe — AI-First Python API for embodied robotics research.

Zero ROS2 learning cost. Same code runs in simulation and on real hardware.

Quick start:
    from threewe import Robot

    async with Robot(backend="gazebo") as robot:
        image = robot.get_camera_image()
        await robot.move_to(x=2.0, y=1.5)
"""

from threewe.exceptions import (
    EmergencyStopError,
    HardwareError,
    NavigationError,
    RobotConnectionError,
    RobotTimeoutError,
    SafetyError,
)
from threewe.experiment import ExperimentProtocol
from threewe.robot import Robot
from threewe.types import (
    BatteryState,
    CameraIntrinsics,
    ExecutionResult,
    ExploreResult,
    IMUData,
    LaserScan,
    MoveResult,
    OccupancyGrid,
    Pose2D,
    RGBDImage,
    Velocity,
)

__version__ = "1.0.0"

__all__ = [
    "Robot",
    "BatteryState",
    "CameraIntrinsics",
    "RobotConnectionError",
    "EmergencyStopError",
    "ExecutionResult",
    "ExperimentProtocol",
    "ExploreResult",
    "HardwareError",
    "IMUData",
    "LaserScan",
    "MoveResult",
    "NavigationError",
    "OccupancyGrid",
    "Pose2D",
    "RGBDImage",
    "SafetyError",
    "RobotTimeoutError",
    "Velocity",
]
