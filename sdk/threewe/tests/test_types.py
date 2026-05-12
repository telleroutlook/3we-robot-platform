# SPDX-License-Identifier: Apache-2.0
"""Tests for threewe core data types."""

import numpy as np

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


class TestPose2D:
    def test_defaults(self):
        pose = Pose2D()
        assert pose.x == 0.0
        assert pose.y == 0.0
        assert pose.theta == 0.0

    def test_values(self):
        pose = Pose2D(x=1.5, y=-2.3, theta=3.14)
        assert pose.x == 1.5
        assert pose.y == -2.3
        assert pose.theta == 3.14

    def test_immutable(self):
        pose = Pose2D(x=1.0, y=2.0, theta=0.5)
        try:
            pose.x = 99.0  # type: ignore[misc]
            raise AssertionError("Should raise")
        except AttributeError:
            pass


class TestVelocity:
    def test_defaults(self):
        vel = Velocity()
        assert vel.vx == 0.0
        assert vel.vy == 0.0
        assert vel.omega == 0.0


class TestMoveResult:
    def test_success(self):
        result = MoveResult(
            success=True,
            final_pose=Pose2D(x=2.0, y=3.0),
            duration=5.2,
            distance=6.1,
            reason="reached",
        )
        assert result.success is True
        assert result.final_pose.x == 2.0
        assert result.reason == "reached"

    def test_failure(self):
        result = MoveResult(
            success=False,
            final_pose=Pose2D(x=1.0, y=1.0),
            reason="collision",
        )
        assert result.success is False
        assert result.reason == "collision"


class TestLaserScan:
    def test_construction(self):
        ranges = np.ones(360, dtype=np.float32)
        angles = np.linspace(0, 2 * np.pi, 360, dtype=np.float32)
        scan = LaserScan(
            ranges=ranges,
            angles=angles,
            angle_min=0.0,
            angle_max=2 * np.pi,
            range_max=12.0,
        )
        assert scan.ranges.shape == (360,)
        assert scan.angles.shape == (360,)
        assert scan.range_max == 12.0


class TestRGBDImage:
    def test_construction(self):
        rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        depth = np.ones((480, 640), dtype=np.float32)
        intrinsics = CameraIntrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0)
        image = RGBDImage(rgb=rgb, depth=depth, intrinsics=intrinsics, timestamp=1.0)
        assert image.rgb.shape == (480, 640, 3)
        assert image.depth.shape == (480, 640)
        assert image.intrinsics.fx == 500.0
        assert image.timestamp == 1.0


class TestIMUData:
    def test_construction(self):
        imu = IMUData(
            acceleration=np.array([0.0, 0.0, 9.81], dtype=np.float32),
            angular_velocity=np.zeros(3, dtype=np.float32),
            orientation=np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        )
        assert imu.acceleration[2] == 9.81
        assert imu.orientation[3] == 1.0


class TestBatteryState:
    def test_construction(self):
        bat = BatteryState(voltage=7.4, percentage=0.85, is_charging=False)
        assert bat.voltage == 7.4
        assert bat.percentage == 0.85
        assert bat.is_charging is False


class TestOccupancyGrid:
    def test_construction(self):
        data = np.full((100, 100), -1, dtype=np.int8)
        grid = OccupancyGrid(data=data, resolution=0.05)
        assert grid.data.shape == (100, 100)
        assert grid.resolution == 0.05


class TestExploreResult:
    def test_defaults(self):
        result = ExploreResult()
        assert result.coverage == 0.0
        assert result.timed_out is False


class TestExecutionResult:
    def test_defaults(self):
        result = ExecutionResult()
        assert result.success is False
        assert result.description == ""
        assert result.images == []
