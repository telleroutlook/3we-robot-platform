# SPDX-License-Identifier: Apache-2.0
"""threewe — AI-First Python API for embodied robotics research.

Zero ROS2 learning cost. Same code runs in simulation and on real hardware.

Quick start:
    from threewe import Robot

    async with Robot(backend="gazebo") as robot:
        image = robot.get_camera_image()
        await robot.move_to(x=2.0, y=1.5)
"""

from threewe.exceptions import (
    ConnectionError,
    EmergencyStopError,
    HardwareError,
    NavigationError,
    SafetyError,
    TimeoutError,
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

__version__ = "0.2.0"

__all__ = [
    "Robot",
    "BatteryState",
    "CameraIntrinsics",
    "ConnectionError",
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
    "TimeoutError",
    "Velocity",
]
