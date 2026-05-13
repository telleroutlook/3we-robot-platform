# SPDX-License-Identifier: Apache-2.0
"""Sensor noise models calibrated from real hardware measurements.

Measured parameters:
- LD06 LiDAR: distance noise σ = 8mm (Gaussian)
- BNO055 IMU: gyro noise σ = 0.0014 rad/s, accel noise σ = 0.01 m/s²
- OV5647 Camera: pixel noise σ = 3 (uint8)
- Mecanum wheel odometry: slip factor 5-15%
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class LidarNoise:
    """Noise model for 2D LiDAR (LD06)."""

    distance_stddev: float = 0.008
    missing_ray_probability: float = 0.01
    max_range: float = 12.0


@dataclass(frozen=True)
class IMUNoise:
    """Noise model for IMU (BNO055)."""

    gyro_stddev: float = 0.0014
    accel_stddev: float = 0.01
    orientation_stddev: float = 0.005


@dataclass(frozen=True)
class CameraNoise:
    """Noise model for RGB camera (OV5647)."""

    pixel_stddev: float = 3.0
    brightness_stddev: float = 5.0
    enable_motion_blur: bool = False


@dataclass(frozen=True)
class OdometryNoise:
    """Noise model for mecanum wheel odometry."""

    slip_factor_min: float = 0.05
    slip_factor_max: float = 0.15
    heading_stddev: float = 0.002


@dataclass(frozen=True)
class SensorNoiseModel:
    """Complete sensor noise model for sim-to-real transfer.

    Calibrated from measurements on the 3we standard_v2 platform.
    Apply to simulation observations to close the sim-to-real gap.

    Usage:
        noise = SensorNoiseModel()
        noisy_scan = noise.apply_lidar(clean_scan)
        noisy_imu = noise.apply_imu(clean_imu)
    """

    lidar: LidarNoise = field(default_factory=LidarNoise)
    imu: IMUNoise = field(default_factory=IMUNoise)
    camera: CameraNoise = field(default_factory=CameraNoise)
    odometry: OdometryNoise = field(default_factory=OdometryNoise)
    seed: int | None = None

    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed)

    def apply_lidar(self, ranges: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
        """Apply noise to a LiDAR scan."""
        rng = rng or self._rng()
        noisy = ranges.copy().astype(np.float32)

        noise = rng.normal(0.0, self.lidar.distance_stddev, size=noisy.shape).astype(np.float32)
        noisy += noise

        mask = rng.random(size=noisy.shape) < self.lidar.missing_ray_probability
        noisy[mask] = self.lidar.max_range

        noisy = np.clip(noisy, 0.0, self.lidar.max_range)
        return noisy

    def apply_imu(
        self,
        acceleration: np.ndarray,
        angular_velocity: np.ndarray,
        orientation: np.ndarray,
        rng: np.random.Generator | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply noise to IMU readings. Returns (accel, gyro, orientation)."""
        rng = rng or self._rng()

        noisy_accel = acceleration + rng.normal(
            0.0, self.imu.accel_stddev, size=acceleration.shape
        ).astype(np.float32)

        noisy_gyro = angular_velocity + rng.normal(
            0.0, self.imu.gyro_stddev, size=angular_velocity.shape
        ).astype(np.float32)

        noisy_ori = orientation + rng.normal(
            0.0, self.imu.orientation_stddev, size=orientation.shape
        ).astype(np.float32)
        norm = np.linalg.norm(noisy_ori)
        if norm > 0:
            noisy_ori = noisy_ori / norm

        return noisy_accel, noisy_gyro, noisy_ori

    def apply_camera(self, image: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
        """Apply noise to an RGB image."""
        rng = rng or self._rng()
        noisy = image.astype(np.float32)

        noise = rng.normal(0.0, self.camera.pixel_stddev, size=noisy.shape).astype(np.float32)
        noisy += noise

        brightness_shift = rng.normal(0.0, self.camera.brightness_stddev)
        noisy += brightness_shift

        return np.clip(noisy, 0, 255).astype(np.uint8)

    def apply_odometry(
        self, pose: np.ndarray, rng: np.random.Generator | None = None
    ) -> np.ndarray:
        """Apply slip and heading noise to odometry pose [x, y, theta]."""
        rng = rng or self._rng()
        noisy = pose.copy().astype(np.float32)

        slip = rng.uniform(self.odometry.slip_factor_min, self.odometry.slip_factor_max)
        direction = rng.choice([-1.0, 1.0])
        noisy[0] *= 1.0 + direction * slip
        noisy[1] *= 1.0 + direction * slip

        noisy[2] += rng.normal(0.0, self.odometry.heading_stddev)

        return noisy
