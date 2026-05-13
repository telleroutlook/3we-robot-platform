# SPDX-License-Identifier: Apache-2.0
"""Mock backend — zero-dependency kinematic simulation.

Provides a lightweight simulation that requires only numpy. Useful for:
- Trying the API without installing ROS2 or Gazebo
- Unit testing
- CI environments
- Quick prototyping

The mock simulates a simple box-shaped room (20m x 15m) and tracks robot
state through basic kinematic integration.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

import numpy as np

from threewe.backends import BackendBase
from threewe.types import (
    BatteryState,
    CameraIntrinsics,
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

_ROOM_WIDTH = 20.0
_ROOM_HEIGHT = 15.0


class MockBackend(BackendBase):
    """Zero-dependency kinematic simulation backend.

    Simulates a robot in a box-shaped room using simple 2D kinematics.
    All state is deterministic — same inputs produce same outputs.
    """

    def __init__(self, config: RobotConfig, scene: str = "office_v2") -> None:
        self._config = config
        self._scene = scene
        self._connected = False

        self._x = 1.0
        self._y = 1.0
        self._theta = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0
        self._last_tick = time.monotonic()

    def connect(self) -> None:
        self._connected = True
        self._last_tick = time.monotonic()

    def disconnect(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _tick(self) -> None:
        """Integrate velocity into position since last call."""
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        if dt <= 0.0 or dt > 1.0:
            return

        cos_t = math.cos(self._theta)
        sin_t = math.sin(self._theta)
        self._x += (self._vx * cos_t - self._vy * sin_t) * dt
        self._y += (self._vx * sin_t + self._vy * cos_t) * dt
        self._theta += self._omega * dt

        self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))

        self._x = max(0.0, min(_ROOM_WIDTH, self._x))
        self._y = max(0.0, min(_ROOM_HEIGHT, self._y))

    def get_camera_image(self) -> np.ndarray:
        self._tick()
        h, w = self._config.api.image_size[1], self._config.api.image_size[0]
        img = np.zeros((h, w, 3), dtype=np.uint8)

        x_norm = self._x / _ROOM_WIDTH
        y_norm = self._y / _ROOM_HEIGHT
        img[:, :, 0] = int(x_norm * 200) + 40
        img[:, :, 1] = int(y_norm * 200) + 40
        img[:, :, 2] = 100

        row = np.linspace(0, 255, w, dtype=np.uint8)
        img[h // 2, :, 2] = row

        return img

    def get_rgbd_image(self) -> RGBDImage:
        rgb = self.get_camera_image()
        h, w = rgb.shape[:2]
        depth = np.full((h, w), 3.0, dtype=np.float32)
        intrinsics = CameraIntrinsics(fx=500.0, fy=500.0, cx=w / 2.0, cy=h / 2.0, width=w, height=h)
        return RGBDImage(rgb=rgb, depth=depth, intrinsics=intrinsics, timestamp=time.time())

    def get_lidar_scan(self) -> LaserScan:
        self._tick()
        n = self._config.api.lidar_points
        angles = np.linspace(0, 2 * math.pi, n, endpoint=False, dtype=np.float32)
        ranges = np.zeros(n, dtype=np.float32)

        for i, angle in enumerate(angles):
            ray_angle = self._theta + float(angle)
            cos_a = math.cos(ray_angle)
            sin_a = math.sin(ray_angle)

            dists: list[float] = []
            if cos_a > 1e-6:
                dists.append((_ROOM_WIDTH - self._x) / cos_a)
            elif cos_a < -1e-6:
                dists.append(-self._x / cos_a)
            if sin_a > 1e-6:
                dists.append((_ROOM_HEIGHT - self._y) / sin_a)
            elif sin_a < -1e-6:
                dists.append(-self._y / sin_a)

            positive = [d for d in dists if d > 0]
            ranges[i] = min(positive) if positive else 12.0

        ranges = np.clip(ranges, 0.0, 12.0)

        return LaserScan(
            ranges=ranges,
            angles=angles,
            angle_min=0.0,
            angle_max=2 * math.pi,
            range_max=12.0,
            timestamp=time.time(),
        )

    def get_pose(self) -> Pose2D:
        self._tick()
        return Pose2D(x=self._x, y=self._y, theta=self._theta)

    def get_velocity(self) -> Velocity:
        return Velocity(vx=self._vx, vy=self._vy, omega=self._omega)

    def get_imu(self) -> IMUData:
        return IMUData(
            acceleration=np.array([0.0, 0.0, 9.81], dtype=np.float32),
            angular_velocity=np.array([0.0, 0.0, self._omega], dtype=np.float32),
            orientation=np.array(
                [0.0, 0.0, math.sin(self._theta / 2), math.cos(self._theta / 2)],
                dtype=np.float32,
            ),
            timestamp=time.time(),
        )

    def get_battery_state(self) -> BatteryState:
        return BatteryState(voltage=7.4, percentage=0.95, is_charging=False)

    def get_map(self) -> OccupancyGrid:
        res = 0.1
        w_cells = int(_ROOM_WIDTH / res)
        h_cells = int(_ROOM_HEIGHT / res)
        grid = np.zeros((h_cells, w_cells), dtype=np.int8)

        grid[0, :] = 100
        grid[-1, :] = 100
        grid[:, 0] = 100
        grid[:, -1] = 100

        return OccupancyGrid(
            data=grid,
            resolution=res,
            origin=Pose2D(x=0.0, y=0.0, theta=0.0),
            timestamp=time.time(),
        )

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        self._vx = vx
        self._vy = vy
        self._omega = omega

    def stop(self) -> None:
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0

    async def move_to(
        self, x: float, y: float, theta: float | None = None, timeout: float = 60.0
    ) -> MoveResult:
        target_x = max(0.0, min(_ROOM_WIDTH, x))
        target_y = max(0.0, min(_ROOM_HEIGHT, y))
        target_theta = theta if theta is not None else self._theta

        distance = math.sqrt((target_x - self._x) ** 2 + (target_y - self._y) ** 2)
        speed = self._config.limits.max_linear_velocity
        duration = distance / speed if speed > 0 else 0.0

        self._x = target_x
        self._y = target_y
        self._theta = target_theta
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0

        return MoveResult(
            success=True,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=distance,
            reason="reached",
        )

    async def move_forward(self, distance: float) -> MoveResult:
        dx = distance * math.cos(self._theta)
        dy = distance * math.sin(self._theta)
        new_x = max(0.0, min(_ROOM_WIDTH, self._x + dx))
        new_y = max(0.0, min(_ROOM_HEIGHT, self._y + dy))

        actual_dist = math.sqrt((new_x - self._x) ** 2 + (new_y - self._y) ** 2)
        self._x = new_x
        self._y = new_y

        speed = self._config.limits.max_linear_velocity
        duration = actual_dist / speed if speed > 0 else 0.0

        return MoveResult(
            success=True,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=actual_dist,
            reason="reached",
        )

    async def rotate(self, angle: float) -> MoveResult:
        self._theta += angle
        self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))

        ang_speed = self._config.limits.max_angular_velocity
        duration = abs(angle) / ang_speed if ang_speed > 0 else 0.0

        return MoveResult(
            success=True,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=0.0,
            reason="reached",
        )

    async def follow_path(self, waypoints: list) -> MoveResult:
        total_distance = 0.0
        for wp in waypoints:
            dx = wp.x - self._x
            dy = wp.y - self._y
            total_distance += math.sqrt(dx * dx + dy * dy)
            self._x = max(0.0, min(_ROOM_WIDTH, wp.x))
            self._y = max(0.0, min(_ROOM_HEIGHT, wp.y))
            if hasattr(wp, "theta") and wp.theta != 0.0:
                self._theta = wp.theta

        speed = self._config.limits.max_linear_velocity
        duration = total_distance / speed if speed > 0 else 0.0

        return MoveResult(
            success=True,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=total_distance,
            reason="reached",
        )

    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        return ExploreResult(
            coverage=1.0,
            duration=min(timeout, 10.0),
            cells_explored=int(_ROOM_WIDTH * _ROOM_HEIGHT / (0.1 * 0.1)),
            timed_out=False,
        )
