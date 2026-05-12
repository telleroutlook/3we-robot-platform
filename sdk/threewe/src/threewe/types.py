# SPDX-License-Identifier: Apache-2.0
"""Core data types for the threewe API.

All sensor data is returned as numpy arrays with standardized shapes and dtypes.
Coordinate system: right-hand, X forward, Y left, Z up. Angles in radians.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True, slots=True)
class Pose2D:
    """2D pose in the map frame."""

    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0


@dataclass(frozen=True, slots=True)
class Velocity:
    """Body-frame velocity."""

    vx: float = 0.0
    vy: float = 0.0
    omega: float = 0.0


@dataclass(frozen=True, slots=True)
class CameraIntrinsics:
    """Pinhole camera intrinsic parameters."""

    fx: float = 0.0
    fy: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    width: int = 640
    height: int = 480


@dataclass(slots=True)
class RGBDImage:
    """RGB-D image pair with intrinsics."""

    rgb: np.ndarray  # (H, W, 3) uint8
    depth: np.ndarray  # (H, W) float32, meters
    intrinsics: CameraIntrinsics
    timestamp: float = 0.0


@dataclass(slots=True)
class LaserScan:
    """2D laser scan."""

    ranges: np.ndarray  # (N,) float32, meters
    angles: np.ndarray  # (N,) float32, radians
    angle_min: float = 0.0
    angle_max: float = 0.0
    range_max: float = 12.0
    timestamp: float = 0.0


@dataclass(slots=True)
class OccupancyGrid:
    """2D occupancy grid map."""

    data: np.ndarray  # (H, W) int8: 0=free, 100=occupied, -1=unknown
    resolution: float = 0.05
    origin: Pose2D = field(default_factory=Pose2D)
    timestamp: float = 0.0


@dataclass(frozen=True, slots=True)
class MoveResult:
    """Result of a navigation action."""

    success: bool
    final_pose: Pose2D
    duration: float = 0.0
    distance: float = 0.0
    reason: str = "reached"


@dataclass(slots=True)
class IMUData:
    """IMU sensor reading."""

    acceleration: np.ndarray  # (3,) m/s²
    angular_velocity: np.ndarray  # (3,) rad/s
    orientation: np.ndarray  # (4,) quaternion [x, y, z, w]
    timestamp: float = 0.0


@dataclass(frozen=True, slots=True)
class BatteryState:
    """Battery status."""

    voltage: float = 0.0
    percentage: float = 0.0
    is_charging: bool = False


@dataclass(frozen=True, slots=True)
class ExploreResult:
    """Result of an exploration action."""

    coverage: float = 0.0
    duration: float = 0.0
    cells_explored: int = 0
    timed_out: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of a VLM instruction execution."""

    success: bool = False
    description: str = ""
    images: list = field(default_factory=list)
