# SPDX-License-Identifier: Apache-2.0
"""Real hardware backend — communicates with physical robot via ROS2.

Bridges to the existing ROS2 stack (micro-ROS Agent → ESP32, Nav2, SLAM, cameras).
Uses the same topic interface as Gazebo (the ros_gz_bridge ensures identical topics).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from threewe.backends import BackendBase
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

if TYPE_CHECKING:
    from threewe.config import RobotConfig


class RealBackend(BackendBase):
    """Real hardware backend communicating via ROS2 topics.

    Requires: ROS2 Jazzy + robot_bringup package running on the robot.
    Subscribes to /camera/image_raw, /scan, /odom, /map, /battery_state.
    Publishes /cmd_vel. Uses Nav2 NavigateToPose action for move_to().
    """

    def __init__(self, config: RobotConfig) -> None:
        self._config = config
        self._ros2_node = None

    def connect(self) -> None:
        try:
            import rclpy  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "ROS2 (rclpy) is required for the real hardware backend. "
                "Install ROS2 Jazzy: https://docs.ros.org/en/jazzy/Installation.html"
            ) from e

        from threewe.backends._ros2_node import ROS2Node

        self._ros2_node = ROS2Node("threewe_real_client", self._config)
        self._ros2_node.connect()

    def disconnect(self) -> None:
        if self._ros2_node is not None:
            self._ros2_node.disconnect()
            self._ros2_node = None

    @property
    def is_connected(self) -> bool:
        return self._ros2_node is not None and self._ros2_node.is_connected

    def get_camera_image(self) -> np.ndarray:
        if self._ros2_node is not None:
            return self._ros2_node.get_camera_image()
        h, w = self._config.api.image_size[1], self._config.api.image_size[0]
        return np.zeros((h, w, 3), dtype=np.uint8)

    def get_rgbd_image(self) -> RGBDImage:
        if self._ros2_node is not None:
            return self._ros2_node.get_rgbd_image()
        from threewe.types import CameraIntrinsics

        h, w = self._config.api.image_size[1], self._config.api.image_size[0]
        return RGBDImage(
            rgb=np.zeros((h, w, 3), dtype=np.uint8),
            depth=np.zeros((h, w), dtype=np.float32),
            intrinsics=CameraIntrinsics(width=w, height=h),
        )

    def get_lidar_scan(self) -> LaserScan:
        if self._ros2_node is not None:
            return self._ros2_node.get_lidar_scan()
        n = self._config.api.lidar_points
        return LaserScan(
            ranges=np.zeros(n, dtype=np.float32),
            angles=np.linspace(0, 2 * np.pi, n, dtype=np.float32),
            angle_min=0.0,
            angle_max=2 * np.pi,
            range_max=12.0,
        )

    def get_pose(self) -> Pose2D:
        if self._ros2_node is not None:
            return self._ros2_node.get_pose()
        return Pose2D()

    def get_velocity(self) -> Velocity:
        if self._ros2_node is not None:
            return self._ros2_node.get_velocity()
        return Velocity()

    def get_imu(self) -> IMUData:
        if self._ros2_node is not None:
            return self._ros2_node.get_imu()
        return IMUData(
            acceleration=np.zeros(3, dtype=np.float32),
            angular_velocity=np.zeros(3, dtype=np.float32),
            orientation=np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        )

    def get_battery_state(self) -> BatteryState:
        if self._ros2_node is not None:
            return self._ros2_node.get_battery_state()
        return BatteryState(voltage=7.4, percentage=1.0, is_charging=False)

    def get_map(self) -> OccupancyGrid:
        if self._ros2_node is not None:
            return self._ros2_node.get_map()
        return OccupancyGrid(data=np.full((100, 100), -1, dtype=np.int8))

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        if self._ros2_node is not None:
            self._ros2_node.set_velocity(vx, vy, omega)

    def stop(self) -> None:
        self.set_velocity(0.0, 0.0, 0.0)

    async def move_to(
        self, x: float, y: float, theta: float | None = None, timeout: float = 60.0
    ) -> MoveResult:
        if self._ros2_node is not None:
            return await self._ros2_node.move_to(x, y, theta, timeout)
        return MoveResult(
            success=True,
            final_pose=Pose2D(x=x, y=y, theta=theta or 0.0),
            reason="reached",
        )

    async def move_forward(self, distance: float) -> MoveResult:
        if self._ros2_node is not None:
            return await self._ros2_node.move_forward(distance)
        return MoveResult(
            success=True,
            final_pose=Pose2D(x=distance, y=0.0),
            distance=distance,
            reason="reached",
        )

    async def rotate(self, angle: float) -> MoveResult:
        if self._ros2_node is not None:
            return await self._ros2_node.rotate(angle)
        return MoveResult(
            success=True,
            final_pose=Pose2D(theta=angle),
            reason="reached",
        )

    async def follow_path(self, waypoints: list) -> MoveResult:
        if self._ros2_node is not None:
            return await self._ros2_node.follow_path(waypoints)
        final = waypoints[-1] if waypoints else Pose2D()
        return MoveResult(
            success=True,
            final_pose=Pose2D(x=final.x, y=final.y, theta=final.theta),
            reason="reached",
        )

    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        if self._ros2_node is not None:
            return await self._ros2_node.explore(timeout)
        return ExploreResult(coverage=0.0, duration=0.0, cells_explored=0)
