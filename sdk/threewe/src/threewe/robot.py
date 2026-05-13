# SPDX-License-Identifier: Apache-2.0
"""Robot — the main user-facing entry point.

Usage:
    from threewe import Robot

    async with Robot(backend="gazebo") as robot:
        image = robot.get_camera_image()
        await robot.move_to(x=2.0, y=1.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from threewe.backends import BackendBase
from threewe.config import RobotConfig, load_config
from threewe.exceptions import RobotConnectionError

if TYPE_CHECKING:
    from threewe.types import (
        BatteryState,
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


class Robot:
    """AI-First interface for controlling a 3we robot.

    Supports three backends:
    - "gazebo": Gazebo Harmonic simulation (CPU, CI, quick iteration)
    - "isaac_sim": NVIDIA Isaac Sim (GPU RL training, domain randomization)
    - "real": Physical robot via ROS2 (Pi 5 + ESP32-S3 + micro-ROS)

    All backends return data in identical formats — code written for one backend
    works on all others without modification.
    """

    def __init__(
        self,
        backend: str = "gazebo",
        config: str | RobotConfig = "standard_v2",
        *,
        hardware: str = "3we_standard_v2",
        scene: str = "office_v2",
        auto_connect: bool = True,
    ) -> None:
        if isinstance(config, str):
            self._config = load_config(config)
        else:
            self._config = config

        from threewe.hal import load_hardware_profile

        self._hardware = load_hardware_profile(hardware)
        self._backend_name = backend
        self._scene = scene
        self._backend: BackendBase = self._create_backend(backend)
        self._auto_connect = auto_connect

    async def __aenter__(self) -> Robot:
        if self._auto_connect:
            self.connect()
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.disconnect()

    @property
    def config(self) -> RobotConfig:
        return self._config

    @property
    def hardware(self):
        return self._hardware

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def is_connected(self) -> bool:
        return self._backend.is_connected

    def connect(self) -> None:
        """Connect to the robot or simulator."""
        self._backend.connect()

    def disconnect(self) -> None:
        """Disconnect from the robot or simulator."""
        if self._backend.is_connected:
            self._backend.disconnect()

    # ─── Perception ───

    def get_camera_image(self) -> np.ndarray:
        """Get RGB image. Returns (H, W, 3) uint8 numpy array."""
        self._ensure_connected()
        return self._backend.get_camera_image()

    get_image = get_camera_image

    def get_rgbd_image(self) -> RGBDImage:
        """Get RGB-D image with depth in meters."""
        self._ensure_connected()
        return self._backend.get_rgbd_image()

    def get_lidar_scan(self) -> LaserScan:
        """Get 2D laser scan."""
        self._ensure_connected()
        return self._backend.get_lidar_scan()

    def get_pose(self) -> Pose2D:
        """Get robot pose in the map frame."""
        self._ensure_connected()
        return self._backend.get_pose()

    def get_velocity(self) -> Velocity:
        """Get current body-frame velocity."""
        self._ensure_connected()
        return self._backend.get_velocity()

    def get_imu(self) -> IMUData:
        """Get IMU sensor data."""
        self._ensure_connected()
        return self._backend.get_imu()

    def get_battery_state(self) -> BatteryState:
        """Get battery voltage, percentage, and charging state."""
        self._ensure_connected()
        return self._backend.get_battery_state()

    def get_map(self) -> OccupancyGrid:
        """Get current SLAM occupancy grid map."""
        self._ensure_connected()
        return self._backend.get_map()

    _DEFAULT_MODALITIES: tuple[str, ...] = ("image", "lidar", "pose", "velocity")

    def get_observation(self, modalities: list[str] | None = None) -> dict[str, np.ndarray]:
        """Get standardized observation dict for VLA/RL model ingestion.

        Args:
            modalities: Which sensor modalities to include. Defaults to
                ("image", "lidar", "pose", "velocity"). Supported:
                "image", "depth", "lidar", "pose", "velocity", "imu", "map".
        """
        self._ensure_connected()
        keys = modalities if modalities is not None else list(self._DEFAULT_MODALITIES)
        obs: dict[str, np.ndarray] = {}

        for key in keys:
            if key == "image":
                obs["image"] = self.get_camera_image()
            elif key == "depth":
                rgbd = self.get_rgbd_image()
                obs["depth"] = rgbd.depth
            elif key == "lidar":
                scan = self.get_lidar_scan()
                obs["lidar"] = scan.ranges
            elif key == "pose":
                pose = self.get_pose()
                obs["pose"] = np.array([pose.x, pose.y, pose.theta], dtype=np.float32)
            elif key == "velocity":
                vel = self.get_velocity()
                obs["velocity"] = np.array([vel.vx, vel.vy, vel.omega], dtype=np.float32)
            elif key == "imu":
                imu = self.get_imu()
                obs["imu"] = np.concatenate(
                    [imu.acceleration, imu.angular_velocity, imu.orientation]
                )
            elif key == "map":
                grid = self.get_map()
                obs["map"] = grid.data.astype(np.float32)
            else:
                raise ValueError(
                    f"Unknown modality '{key}'. Supported: "
                    "image, depth, lidar, pose, velocity, imu, map"
                )

        return obs

    # ─── Action ───

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        """Command body velocity. Must be called continuously or timeout stops motors."""
        self._ensure_connected()
        self._clamp_and_send(vx, vy, omega)

    def stop(self) -> None:
        """Immediately stop all motion."""
        self._ensure_connected()
        self._backend.stop()

    async def move_to(
        self, x: float, y: float, theta: float | None = None, timeout: float = 60.0
    ) -> MoveResult:
        """Navigate to target pose using Nav2 path planning."""
        self._ensure_connected()
        return await self._backend.move_to(x, y, theta, timeout)

    async def move_forward(self, distance: float) -> MoveResult:
        """Drive straight forward by the specified distance (meters)."""
        self._ensure_connected()
        return await self._backend.move_forward(distance)

    async def rotate(self, angle: float) -> MoveResult:
        """Rotate in place by the specified angle (radians, positive=CCW)."""
        self._ensure_connected()
        return await self._backend.rotate(angle)

    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        """Autonomously explore unknown areas until map is complete or timeout."""
        self._ensure_connected()
        return await self._backend.explore(timeout)

    async def follow_path(self, waypoints: list[Pose2D]) -> MoveResult:
        """Follow a sequence of waypoints in order."""
        self._ensure_connected()
        return await self._backend.follow_path(waypoints)

    # ─── AI Integration ───

    def execute_action(self, action: np.ndarray) -> None:
        """Execute a policy network output action vector.

        Expected shape: (3,) normalized to [-1, 1] as [vx, vy, omega].
        Scaled by configured max velocities.
        """
        self._ensure_connected()
        limits = self._config.limits
        vx = float(action[0]) * limits.max_linear_velocity
        vy = float(action[1]) * limits.max_linear_velocity
        omega = float(action[2]) * limits.max_angular_velocity
        self._clamp_and_send(vx, vy, omega)

    async def execute_instruction(self, instruction: str) -> ExecutionResult:
        """Execute a natural language instruction using VLM reasoning.

        Requires the `ai` extra: pip install threewe[ai]
        """
        self._ensure_connected()
        from threewe.ai.vlm_runner import execute_vlm_instruction

        return await execute_vlm_instruction(self, instruction)

    # ─── Internal ───

    def _ensure_connected(self) -> None:
        if not self._backend.is_connected:
            raise RobotConnectionError("Robot is not connected. Call robot.connect() first.")

    def _clamp_and_send(self, vx: float, vy: float, omega: float) -> None:
        limits = self._config.limits
        vx = max(-limits.max_linear_velocity, min(limits.max_linear_velocity, vx))
        vy = max(-limits.max_linear_velocity, min(limits.max_linear_velocity, vy))
        omega = max(-limits.max_angular_velocity, min(limits.max_angular_velocity, omega))
        self._backend.set_velocity(vx, vy, omega)

    def _create_backend(self, backend: str) -> BackendBase:
        if backend == "gazebo":
            from threewe.backends.gazebo import GazeboBackend

            return GazeboBackend(config=self._config, scene=self._scene)
        elif backend == "real":
            from threewe.backends.real import RealBackend

            return RealBackend(config=self._config)
        elif backend == "isaac_sim":
            from threewe.backends.isaac_sim import IsaacSimBackend, IsaacSimConfig

            return IsaacSimBackend(config=IsaacSimConfig(scene=self._scene))
        elif backend == "mock":
            from threewe.backends.mock import MockBackend

            return MockBackend(config=self._config, scene=self._scene)
        else:
            raise ValueError(
                f"Unknown backend '{backend}'. Choose from: 'gazebo', 'real', 'isaac_sim', 'mock'"
            )
