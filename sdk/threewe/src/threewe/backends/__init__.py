# SPDX-License-Identifier: Apache-2.0
"""Backend Abstraction Layer — the Sim2Real consistency contract.

All backends (Gazebo, Isaac Sim, Real Hardware) implement this interface.
Users interact with the Robot class which delegates to the active backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

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


class BackendBase(ABC):
    """Abstract base for all robot backends.

    Consistency contract guarantees:
    - Image: (H, W, 3) uint8 BGR
    - Depth: (H, W) float32, meters, invalid=0.0
    - LiDAR: (N,) float32, meters, uniform angular sampling
    - Pose: right-hand, X forward, Y left, Z up, radians
    - Velocity: m/s linear, rad/s angular
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the backend."""

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly disconnect from the backend."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the backend is currently connected."""

    @abstractmethod
    def get_camera_image(self) -> np.ndarray:
        """Get RGB image. Returns (H, W, 3) uint8."""

    @abstractmethod
    def get_rgbd_image(self) -> RGBDImage:
        """Get RGB-D image pair."""

    @abstractmethod
    def get_lidar_scan(self) -> LaserScan:
        """Get 2D laser scan."""

    @abstractmethod
    def get_pose(self) -> Pose2D:
        """Get robot pose in map frame."""

    @abstractmethod
    def get_velocity(self) -> Velocity:
        """Get current body velocity."""

    @abstractmethod
    def get_imu(self) -> IMUData:
        """Get IMU reading."""

    @abstractmethod
    def get_battery_state(self) -> BatteryState:
        """Get battery status."""

    @abstractmethod
    def get_map(self) -> OccupancyGrid:
        """Get current occupancy grid map."""

    @abstractmethod
    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        """Command body velocity. Must be called continuously or timeout stops motors."""

    @abstractmethod
    def stop(self) -> None:
        """Immediately stop all motion."""

    @abstractmethod
    async def move_to(
        self, x: float, y: float, theta: float | None = None, timeout: float = 60.0
    ) -> MoveResult:
        """Navigate to target pose using path planning."""

    @abstractmethod
    async def move_forward(self, distance: float) -> MoveResult:
        """Drive forward by the specified distance in meters."""

    @abstractmethod
    async def rotate(self, angle: float) -> MoveResult:
        """Rotate in place by the specified angle in radians."""

    @abstractmethod
    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        """Autonomously explore unknown areas."""
