# SPDX-License-Identifier: Apache-2.0
"""Mock backend — zero-dependency kinematic simulation.

Provides a lightweight simulation that requires only numpy. Useful for:
- Trying the API without installing ROS2 or Gazebo
- Unit testing
- CI environments
- Quick prototyping

The mock simulates 2D environments with configurable obstacle layouts,
Gaussian sensor noise, and collision detection.
"""

from __future__ import annotations

import asyncio
import math
import time
from typing import TYPE_CHECKING

import numpy as np

from threewe.backends import BackendBase
from threewe.backends.mock_scenes import Obstacle, get_scene
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

_ROBOT_RADIUS = 0.15
_LIDAR_NOISE_STD = 0.008
_MOVE_STEP = 0.05


class MockBackend(BackendBase):
    """Zero-dependency kinematic simulation backend.

    Simulates a robot in a 2D environment with obstacles using simple
    kinematics. Includes Gaussian sensor noise and collision detection.
    """

    def __init__(
        self, config: RobotConfig, scene: str = "office_v2", *, verbose: bool = False
    ) -> None:
        self._config = config
        self._scene_name = scene
        self._scene = get_scene(scene)
        self._connected = False
        self._verbose = verbose

        self._x = 1.0
        self._y = 1.0
        self._theta = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0
        self._last_tick = time.monotonic()
        self._rng = np.random.default_rng(42)

    def connect(self) -> None:
        self._connected = True
        self._last_tick = time.monotonic()
        if self._verbose:
            self._log(f"Robot initialized  backend=mock  scene={self._scene_name}")

    def disconnect(self) -> None:
        self._connected = False
        if self._verbose:
            self._log("Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _log(self, msg: str) -> None:
        print(f"\033[36m[3we]\033[0m {msg}", flush=True)

    def _tick(self) -> None:
        """Integrate velocity into position since last call."""
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        if dt <= 0.0 or dt > 1.0:
            return

        cos_t = math.cos(self._theta)
        sin_t = math.sin(self._theta)
        new_x = self._x + (self._vx * cos_t - self._vy * sin_t) * dt
        new_y = self._y + (self._vx * sin_t + self._vy * cos_t) * dt

        if not self._collides(new_x, new_y):
            self._x = new_x
            self._y = new_y

        self._theta += self._omega * dt
        self._theta = math.atan2(math.sin(self._theta), math.cos(self._theta))

    def _collides(self, x: float, y: float) -> bool:
        """Check if position collides with walls or obstacles."""
        r = _ROBOT_RADIUS
        if x - r < 0 or x + r > self._scene.width:
            return True
        if y - r < 0 or y + r > self._scene.height:
            return True

        for obs in self._scene.obstacles:
            if self._circle_rect_collision(x, y, r, obs):
                return True
        return False

    @staticmethod
    def _circle_rect_collision(cx: float, cy: float, r: float, obs: Obstacle) -> bool:
        nearest_x = max(obs.x_min, min(cx, obs.x_max))
        nearest_y = max(obs.y_min, min(cy, obs.y_max))
        dx = cx - nearest_x
        dy = cy - nearest_y
        return (dx * dx + dy * dy) < (r * r)

    def _raycast(self, angle: float) -> float:
        """Cast a ray from robot position and return distance to first hit."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        min_dist = self._scene.width + self._scene.height

        # Walls
        if cos_a > 1e-6:
            min_dist = min(min_dist, (self._scene.width - self._x) / cos_a)
        elif cos_a < -1e-6:
            min_dist = min(min_dist, -self._x / cos_a)
        if sin_a > 1e-6:
            min_dist = min(min_dist, (self._scene.height - self._y) / sin_a)
        elif sin_a < -1e-6:
            min_dist = min(min_dist, -self._y / sin_a)

        # Obstacles — slab method for AABB ray intersection
        for obs in self._scene.obstacles:
            d = self._ray_aabb_dist(cos_a, sin_a, obs)
            if d is not None and d < min_dist:
                min_dist = d

        return max(0.12, min(min_dist, 12.0))

    def _ray_aabb_dist(self, cos_a: float, sin_a: float, obs: Obstacle) -> float | None:
        """Ray-AABB intersection distance using slab method."""
        if abs(cos_a) < 1e-9:
            if self._x < obs.x_min or self._x > obs.x_max:
                return None
            t_min_x = -1e30
            t_max_x = 1e30
        else:
            inv_dx = 1.0 / cos_a
            t1 = (obs.x_min - self._x) * inv_dx
            t2 = (obs.x_max - self._x) * inv_dx
            t_min_x = min(t1, t2)
            t_max_x = max(t1, t2)

        if abs(sin_a) < 1e-9:
            if self._y < obs.y_min or self._y > obs.y_max:
                return None
            t_min_y = -1e30
            t_max_y = 1e30
        else:
            inv_dy = 1.0 / sin_a
            t1 = (obs.y_min - self._y) * inv_dy
            t2 = (obs.y_max - self._y) * inv_dy
            t_min_y = min(t1, t2)
            t_max_y = max(t1, t2)

        t_enter = max(t_min_x, t_min_y)
        t_exit = min(t_max_x, t_max_y)

        if t_enter > t_exit or t_exit < 0:
            return None
        t = t_enter if t_enter > 0 else t_exit
        return t if t > 0 else None

    def get_camera_image(self) -> np.ndarray:
        self._tick()
        h, w = self._config.api.image_size[1], self._config.api.image_size[0]
        img = np.zeros((h, w, 3), dtype=np.uint8)

        x_norm = self._x / self._scene.width
        y_norm = self._y / self._scene.height
        img[:, :, 0] = int(x_norm * 200) + 40
        img[:, :, 1] = int(y_norm * 200) + 40
        img[:, :, 2] = 100

        row = np.linspace(0, 255, w, dtype=np.uint8)
        img[h // 2, :, 2] = row

        return img

    def get_rgbd_image(self) -> RGBDImage:
        rgb = self.get_camera_image()
        h, w = rgb.shape[:2]
        front_dist = self._raycast(self._theta)
        depth = np.full((h, w), front_dist, dtype=np.float32)
        intrinsics = CameraIntrinsics(fx=500.0, fy=500.0, cx=w / 2.0, cy=h / 2.0, width=w, height=h)
        return RGBDImage(rgb=rgb, depth=depth, intrinsics=intrinsics, timestamp=time.time())

    def get_lidar_scan(self) -> LaserScan:
        self._tick()
        n = self._config.api.lidar_points
        angles = np.linspace(0, 2 * math.pi, n, endpoint=False, dtype=np.float32)
        ranges = np.zeros(n, dtype=np.float32)

        for i, angle in enumerate(angles):
            ray_angle = self._theta + float(angle)
            ranges[i] = self._raycast(ray_angle)

        noise = self._rng.normal(0.0, _LIDAR_NOISE_STD, size=n).astype(np.float32)
        ranges = np.clip(ranges + noise, 0.12, 12.0)

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

    def get_wheel_speeds(self) -> np.ndarray:
        wheel_radius = 0.0325  # 65mm mecanum wheel
        wheel_base_x = 0.08
        wheel_base_y = 0.09
        k = wheel_base_x + wheel_base_y
        speeds_rad = np.array(
            [
                (self._vx - self._vy - k * self._omega) / wheel_radius,
                (self._vx + self._vy + k * self._omega) / wheel_radius,
                (self._vx + self._vy - k * self._omega) / wheel_radius,
                (self._vx - self._vy + k * self._omega) / wheel_radius,
            ],
            dtype=np.float32,
        )
        speeds_rpm = speeds_rad * 60.0 / (2.0 * np.pi)
        noise = self._rng.normal(0.0, 2.0, size=(4,)).astype(np.float32)
        return speeds_rpm + noise

    def get_motor_current(self) -> np.ndarray:
        base_current = 0.05  # Amps idle per motor
        speed_factor = 0.003  # Amps per RPM load
        wheel_speeds = self.get_wheel_speeds()
        current = base_current + np.abs(wheel_speeds) * speed_factor
        noise = self._rng.normal(0.0, 0.015, size=(4,)).astype(np.float32)
        return np.maximum(current + noise, 0.0).astype(np.float32)

    def get_map(self) -> OccupancyGrid:
        res = 0.1
        w_cells = int(self._scene.width / res)
        h_cells = int(self._scene.height / res)
        grid = np.zeros((h_cells, w_cells), dtype=np.int8)

        grid[0, :] = 100
        grid[-1, :] = 100
        grid[:, 0] = 100
        grid[:, -1] = 100

        for obs in self._scene.obstacles:
            x0 = max(0, int(obs.x_min / res))
            x1 = min(w_cells, int(obs.x_max / res))
            y0 = max(0, int(obs.y_min / res))
            y1 = min(h_cells, int(obs.y_max / res))
            grid[y0:y1, x0:x1] = 100

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
        target_x = max(_ROBOT_RADIUS, min(self._scene.width - _ROBOT_RADIUS, x))
        target_y = max(_ROBOT_RADIUS, min(self._scene.height - _ROBOT_RADIUS, y))
        target_theta = theta if theta is not None else self._theta

        start_x, start_y = self._x, self._y
        total_distance = math.sqrt((target_x - self._x) ** 2 + (target_y - self._y) ** 2)
        speed = self._config.limits.max_linear_velocity

        if total_distance < 0.01:
            self._theta = target_theta
            return MoveResult(
                success=True,
                final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
                duration=0.0,
                distance=0.0,
                reason="reached",
            )

        if self._verbose:
            self._log(f"Navigating to ({target_x:.1f}, {target_y:.1f})...")
            self._log(f"Planning path... distance={total_distance:.1f}m")

        dx = (target_x - self._x) / total_distance
        dy = (target_y - self._y) / total_distance
        moved = 0.0
        blocked = False
        report_interval = max(1, int(total_distance / _MOVE_STEP / 5))
        step_count = 0

        while moved < total_distance:
            step = min(_MOVE_STEP, total_distance - moved)
            new_x = self._x + dx * step
            new_y = self._y + dy * step
            if self._collides(new_x, new_y):
                blocked = True
                break
            self._x = new_x
            self._y = new_y
            moved += step
            step_count += 1

            if self._verbose and step_count % report_interval == 0:
                heading = math.degrees(math.atan2(dy, dx))
                remaining = total_distance - moved
                self._log(
                    f"  pos=({self._x:.1f}, {self._y:.1f})"
                    f"  heading={heading:.0f}°"
                    f"  remaining={remaining:.1f}m"
                )
                await asyncio.sleep(0.15)

        self._theta = target_theta
        self._vx = 0.0
        self._vy = 0.0
        self._omega = 0.0

        actual_dist = math.sqrt((self._x - start_x) ** 2 + (self._y - start_y) ** 2)
        duration = actual_dist / speed if speed > 0 else 0.0

        if self._verbose:
            if not blocked:
                self._log(f"Goal reached  distance={actual_dist:.1f}m  time={duration:.1f}s")
            else:
                self._log(f"Blocked by obstacle at ({self._x:.1f}, {self._y:.1f})")

        return MoveResult(
            success=not blocked,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=actual_dist,
            reason="reached" if not blocked else "collision",
        )

    async def move_forward(self, distance: float) -> MoveResult:
        cos_t = math.cos(self._theta)
        sin_t = math.sin(self._theta)
        start_x, start_y = self._x, self._y
        speed = self._config.limits.max_linear_velocity

        moved = 0.0
        blocked = False
        sign = 1.0 if distance >= 0 else -1.0
        abs_dist = abs(distance)

        while moved < abs_dist:
            step = min(_MOVE_STEP, abs_dist - moved)
            new_x = self._x + cos_t * step * sign
            new_y = self._y + sin_t * step * sign
            if self._collides(new_x, new_y):
                blocked = True
                break
            self._x = new_x
            self._y = new_y
            moved += step

        actual_dist = math.sqrt((self._x - start_x) ** 2 + (self._y - start_y) ** 2)
        duration = actual_dist / speed if speed > 0 else 0.0

        return MoveResult(
            success=not blocked,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=actual_dist,
            reason="reached" if not blocked else "collision",
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
        blocked = False

        for wp in waypoints:
            result = await self.move_to(wp.x, wp.y, getattr(wp, "theta", None))
            total_distance += result.distance
            if not result.success:
                blocked = True
                break

        speed = self._config.limits.max_linear_velocity
        duration = total_distance / speed if speed > 0 else 0.0

        return MoveResult(
            success=not blocked,
            final_pose=Pose2D(x=self._x, y=self._y, theta=self._theta),
            duration=duration,
            distance=total_distance,
            reason="reached" if not blocked else "collision",
        )

    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        return ExploreResult(
            coverage=1.0,
            duration=min(timeout, 10.0),
            cells_explored=int(self._scene.width * self._scene.height / (0.1 * 0.1)),
            timed_out=False,
        )
