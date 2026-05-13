# SPDX-License-Identifier: Apache-2.0
"""Domain randomization configuration for sim-to-real transfer.

Supports randomizing:
- Physics: mass, friction, motor torque noise
- Visuals: textures, lighting, shadows
- Sensor noise parameters (via SensorNoiseModel scaling)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class PhysicsRandomization:
    """Physics parameter randomization ranges."""

    mass_scale_range: tuple[float, float] = (0.9, 1.1)
    friction_scale_range: tuple[float, float] = (0.8, 1.2)
    motor_torque_noise_stddev: float = 0.05
    gravity_noise_stddev: float = 0.01


@dataclass
class VisualRandomization:
    """Visual appearance randomization."""

    randomize_textures: bool = True
    randomize_lighting: bool = True
    randomize_shadows: bool = True
    lighting_intensity_range: tuple[float, float] = (0.5, 1.5)
    color_jitter: float = 0.1


@dataclass
class SensorRandomization:
    """Sensor noise parameter scaling."""

    lidar_noise_scale_range: tuple[float, float] = (0.5, 2.0)
    imu_noise_scale_range: tuple[float, float] = (0.5, 2.0)
    camera_noise_scale_range: tuple[float, float] = (0.5, 2.0)
    odometry_slip_scale_range: tuple[float, float] = (0.5, 2.0)


@dataclass
class DomainRandomization:
    """Complete domain randomization configuration.

    Usage:
        dr = DomainRandomization()
        params = dr.sample()  # Get randomized parameters for one episode
        dr = DomainRandomization.from_yaml("configs/domain_randomization.yaml")
    """

    physics: PhysicsRandomization = field(default_factory=PhysicsRandomization)
    visual: VisualRandomization = field(default_factory=VisualRandomization)
    sensor: SensorRandomization = field(default_factory=SensorRandomization)
    seed: int | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> DomainRandomization:
        """Load domain randomization config from YAML file."""
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML is required to load DR configs. Install with: pip install pyyaml"
            ) from e

        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)

        physics_data = data.get("physics", {})
        visual_data = data.get("visual", {})
        sensor_data = data.get("sensor", {})

        physics = PhysicsRandomization(
            mass_scale_range=tuple(physics_data.get("mass_scale_range", [0.9, 1.1])),
            friction_scale_range=tuple(physics_data.get("friction_scale_range", [0.8, 1.2])),
            motor_torque_noise_stddev=physics_data.get("motor_torque_noise_stddev", 0.05),
            gravity_noise_stddev=physics_data.get("gravity_noise_stddev", 0.01),
        )

        visual = VisualRandomization(
            randomize_textures=visual_data.get("randomize_textures", True),
            randomize_lighting=visual_data.get("randomize_lighting", True),
            randomize_shadows=visual_data.get("randomize_shadows", True),
            lighting_intensity_range=tuple(visual_data.get("lighting_intensity_range", [0.5, 1.5])),
            color_jitter=visual_data.get("color_jitter", 0.1),
        )

        sensor = SensorRandomization(
            lidar_noise_scale_range=tuple(sensor_data.get("lidar_noise_scale_range", [0.5, 2.0])),
            imu_noise_scale_range=tuple(sensor_data.get("imu_noise_scale_range", [0.5, 2.0])),
            camera_noise_scale_range=tuple(sensor_data.get("camera_noise_scale_range", [0.5, 2.0])),
            odometry_slip_scale_range=tuple(
                sensor_data.get("odometry_slip_scale_range", [0.5, 2.0])
            ),
        )

        return cls(
            physics=physics,
            visual=visual,
            sensor=sensor,
            seed=data.get("seed"),
        )

    def sample(self, rng: np.random.Generator | None = None) -> dict[str, Any]:
        """Sample a set of randomized parameters for one episode.

        Returns a dict with randomized physics, visual, and sensor scaling factors.
        """
        rng = rng or np.random.default_rng(self.seed)

        return {
            "mass_scale": float(rng.uniform(*self.physics.mass_scale_range)),
            "friction_scale": float(rng.uniform(*self.physics.friction_scale_range)),
            "motor_torque_noise": float(rng.normal(0.0, self.physics.motor_torque_noise_stddev)),
            "gravity_noise": float(rng.normal(0.0, self.physics.gravity_noise_stddev)),
            "lighting_intensity": float(rng.uniform(*self.visual.lighting_intensity_range)),
            "color_jitter": float(rng.uniform(-self.visual.color_jitter, self.visual.color_jitter)),
            "lidar_noise_scale": float(rng.uniform(*self.sensor.lidar_noise_scale_range)),
            "imu_noise_scale": float(rng.uniform(*self.sensor.imu_noise_scale_range)),
            "camera_noise_scale": float(rng.uniform(*self.sensor.camera_noise_scale_range)),
            "odometry_slip_scale": float(rng.uniform(*self.sensor.odometry_slip_scale_range)),
        }
