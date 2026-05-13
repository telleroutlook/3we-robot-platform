# SPDX-License-Identifier: Apache-2.0
"""Shared test fixtures for the threewe test suite."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pytest

from threewe.config import RobotConfig, load_config
from threewe.types import (
    BatteryState,
    CameraIntrinsics,
    IMUData,
    LaserScan,
    OccupancyGrid,
    Pose2D,
    RGBDImage,
    Velocity,
)


@pytest.fixture
def default_config() -> RobotConfig:
    return load_config("standard_v2")


@pytest.fixture
def mock_backend():
    """A fully mocked BackendBase returning sensible defaults."""
    backend = MagicMock()
    type(backend).is_connected = PropertyMock(return_value=True)
    backend.get_camera_image.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    backend.get_rgbd_image.return_value = RGBDImage(
        rgb=np.zeros((480, 640, 3), dtype=np.uint8),
        depth=np.zeros((480, 640), dtype=np.float32),
        intrinsics=CameraIntrinsics(width=640, height=480),
    )
    backend.get_lidar_scan.return_value = LaserScan(
        ranges=np.ones(360, dtype=np.float32),
        angles=np.linspace(0, 2 * np.pi, 360, dtype=np.float32),
        angle_min=0.0,
        angle_max=2 * np.pi,
        range_max=12.0,
    )
    backend.get_pose.return_value = Pose2D(x=1.0, y=2.0, theta=0.5)
    backend.get_velocity.return_value = Velocity(vx=0.1, vy=0.0, omega=0.05)
    backend.get_imu.return_value = IMUData(
        acceleration=np.array([0.0, 0.0, 9.81], dtype=np.float32),
        angular_velocity=np.zeros(3, dtype=np.float32),
        orientation=np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
    )
    backend.get_battery_state.return_value = BatteryState(
        voltage=7.4, percentage=0.9, is_charging=False
    )
    backend.get_map.return_value = OccupancyGrid(data=np.full((100, 100), -1, dtype=np.int8))
    return backend


@pytest.fixture
def connected_robot(mock_backend, default_config):
    """A Robot instance with a mocked backend, already connected."""
    from threewe.robot import Robot

    robot = Robot(backend="gazebo", config=default_config, auto_connect=False)
    robot._backend = mock_backend
    return robot


@pytest.fixture
def mock_robot_for_recording(mock_backend, default_config):
    """Robot configured for trajectory recording tests."""
    from threewe.robot import Robot

    robot = Robot(backend="gazebo", config=default_config, auto_connect=False)
    robot._backend = mock_backend
    return robot
