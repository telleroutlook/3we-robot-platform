# SPDX-License-Identifier: Apache-2.0
"""Tests for the MockBackend — zero-dependency kinematic simulation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from threewe.backends.mock import MockBackend
from threewe.config import RobotConfig
from threewe.types import (
    BatteryState,
    ExploreResult,
    IMUData,
    LaserScan,
    MoveResult,
    OccupancyGrid,
    Pose2D,
    RGBDImage,
    Velocity,
)


@pytest.fixture
def config() -> RobotConfig:
    return RobotConfig()


@pytest.fixture
def backend(config: RobotConfig) -> MockBackend:
    b = MockBackend(config=config, scene="office_v2")
    b.connect()
    return b


class TestConnection:
    def test_initial_state_not_connected(self, config: RobotConfig) -> None:
        b = MockBackend(config=config)
        assert not b.is_connected

    def test_connect(self, config: RobotConfig) -> None:
        b = MockBackend(config=config)
        b.connect()
        assert b.is_connected

    def test_disconnect(self, backend: MockBackend) -> None:
        backend.disconnect()
        assert not backend.is_connected


class TestPerception:
    def test_get_camera_image_shape(self, backend: MockBackend) -> None:
        img = backend.get_camera_image()
        assert isinstance(img, np.ndarray)
        assert img.shape == (480, 640, 3)
        assert img.dtype == np.uint8

    def test_get_rgbd_image(self, backend: MockBackend) -> None:
        rgbd = backend.get_rgbd_image()
        assert isinstance(rgbd, RGBDImage)
        assert rgbd.rgb.shape == (480, 640, 3)
        assert rgbd.depth.shape == (480, 640)
        assert rgbd.depth.dtype == np.float32
        assert rgbd.intrinsics.width == 640
        assert rgbd.intrinsics.height == 480
        assert rgbd.timestamp > 0

    def test_get_lidar_scan(self, backend: MockBackend) -> None:
        scan = backend.get_lidar_scan()
        assert isinstance(scan, LaserScan)
        assert scan.ranges.shape == (360,)
        assert scan.angles.shape == (360,)
        assert scan.ranges.dtype == np.float32
        assert np.all(scan.ranges > 0)
        assert np.all(scan.ranges <= 12.0)

    def test_get_pose_initial(self, backend: MockBackend) -> None:
        pose = backend.get_pose()
        assert isinstance(pose, Pose2D)
        assert pose.x == pytest.approx(1.0)
        assert pose.y == pytest.approx(1.0)
        assert pose.theta == pytest.approx(0.0)

    def test_get_velocity_initial(self, backend: MockBackend) -> None:
        vel = backend.get_velocity()
        assert isinstance(vel, Velocity)
        assert vel.vx == 0.0
        assert vel.vy == 0.0
        assert vel.omega == 0.0

    def test_get_imu(self, backend: MockBackend) -> None:
        imu = backend.get_imu()
        assert isinstance(imu, IMUData)
        assert imu.acceleration.shape == (3,)
        assert imu.angular_velocity.shape == (3,)
        assert imu.orientation.shape == (4,)
        assert imu.acceleration[2] == pytest.approx(9.81)

    def test_get_battery_state(self, backend: MockBackend) -> None:
        battery = backend.get_battery_state()
        assert isinstance(battery, BatteryState)
        assert battery.voltage == pytest.approx(7.4)
        assert 0.0 <= battery.percentage <= 1.0
        assert battery.is_charging is False

    def test_get_map(self, backend: MockBackend) -> None:
        grid = backend.get_map()
        assert isinstance(grid, OccupancyGrid)
        assert grid.data.dtype == np.int8
        assert grid.resolution == pytest.approx(0.1)
        assert grid.data[0, 0] == 100
        assert grid.data[5, 5] == 0


class TestAction:
    def test_set_velocity(self, backend: MockBackend) -> None:
        backend.set_velocity(0.5, 0.1, 0.2)
        vel = backend.get_velocity()
        assert vel.vx == pytest.approx(0.5)
        assert vel.vy == pytest.approx(0.1)
        assert vel.omega == pytest.approx(0.2)

    def test_stop(self, backend: MockBackend) -> None:
        backend.set_velocity(1.0, 0.5, 0.3)
        backend.stop()
        vel = backend.get_velocity()
        assert vel.vx == 0.0
        assert vel.vy == 0.0
        assert vel.omega == 0.0

    @pytest.mark.asyncio
    async def test_move_to(self, backend: MockBackend) -> None:
        result = await backend.move_to(5.0, 3.0)
        assert isinstance(result, MoveResult)
        assert result.success is True
        assert result.reason == "reached"
        assert result.final_pose.x == pytest.approx(5.0)
        assert result.final_pose.y == pytest.approx(3.0)
        assert result.distance > 0

        pose = backend.get_pose()
        assert pose.x == pytest.approx(5.0)
        assert pose.y == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_move_to_with_theta(self, backend: MockBackend) -> None:
        result = await backend.move_to(2.0, 2.0, theta=math.pi / 2)
        assert result.final_pose.theta == pytest.approx(math.pi / 2)

    @pytest.mark.asyncio
    async def test_move_to_clamped(self, backend: MockBackend) -> None:
        result = await backend.move_to(100.0, 100.0)
        assert result.final_pose.x == pytest.approx(20.0)
        assert result.final_pose.y == pytest.approx(15.0)

    @pytest.mark.asyncio
    async def test_move_forward(self, backend: MockBackend) -> None:
        result = await backend.move_forward(2.0)
        assert result.success is True
        pose = backend.get_pose()
        assert pose.x == pytest.approx(3.0, abs=0.01)
        assert pose.y == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_move_forward_with_angle(self, backend: MockBackend) -> None:
        await backend.rotate(math.pi / 2)
        await backend.move_forward(2.0)
        pose = backend.get_pose()
        assert pose.x == pytest.approx(1.0, abs=0.01)
        assert pose.y == pytest.approx(3.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_rotate(self, backend: MockBackend) -> None:
        result = await backend.rotate(math.pi / 4)
        assert result.success is True
        pose = backend.get_pose()
        assert pose.theta == pytest.approx(math.pi / 4)

    @pytest.mark.asyncio
    async def test_rotate_wraps(self, backend: MockBackend) -> None:
        await backend.rotate(math.pi)
        await backend.rotate(math.pi)
        pose = backend.get_pose()
        assert -math.pi <= pose.theta <= math.pi

    @pytest.mark.asyncio
    async def test_follow_path(self, backend: MockBackend) -> None:
        waypoints = [
            Pose2D(x=3.0, y=1.0),
            Pose2D(x=3.0, y=4.0),
            Pose2D(x=5.0, y=4.0),
        ]
        result = await backend.follow_path(waypoints)
        assert result.success is True
        assert result.distance > 0
        pose = backend.get_pose()
        assert pose.x == pytest.approx(5.0)
        assert pose.y == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_explore(self, backend: MockBackend) -> None:
        result = await backend.explore(timeout=30.0)
        assert isinstance(result, ExploreResult)
        assert result.coverage == pytest.approx(1.0)
        assert result.cells_explored > 0
        assert result.timed_out is False


class TestKinematics:
    def test_lidar_consistency_with_pose(self, backend: MockBackend) -> None:
        """LiDAR ranges should be consistent with position in the box room."""
        scan = backend.get_lidar_scan()
        forward_idx = 0
        # At x=1.0 facing forward, wall is at x=20.0 → distance=19m, but clamped to range_max=12
        assert scan.ranges[forward_idx] == pytest.approx(12.0)

        # Check backward ray (index ~N/2) — wall is at x=0 → distance=1.0
        n = len(scan.ranges)
        backward_idx = n // 2
        assert scan.ranges[backward_idx] == pytest.approx(1.0, abs=0.2)

    def test_imu_orientation_matches_theta(self, backend: MockBackend) -> None:
        """IMU quaternion z-component should reflect robot heading."""
        imu = backend.get_imu()
        assert imu.orientation[2] == pytest.approx(math.sin(0.0 / 2))
        assert imu.orientation[3] == pytest.approx(math.cos(0.0 / 2))
