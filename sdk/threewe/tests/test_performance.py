# SPDX-License-Identifier: Apache-2.0
"""Performance benchmarks for critical SDK code paths.

Uses pytest-benchmark to measure throughput of:
- SensorNoiseModel (all sensor types)
- DomainRandomization.sample
- MockBackend sensor reads (proxy for control loop budget)

Run with: pytest tests/test_performance.py --benchmark-only
"""

from __future__ import annotations

import numpy as np
import pytest

from threewe.sim.domain_randomization import DomainRandomization
from threewe.sim.noise import SensorNoiseModel


@pytest.fixture()
def noise_model():
    return SensorNoiseModel(seed=42)


@pytest.fixture()
def lidar_ranges():
    return np.ones(360, dtype=np.float32) * 5.0


@pytest.fixture()
def camera_image():
    return np.random.default_rng(0).integers(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture()
def imu_data():
    return (
        np.array([0.0, 0.0, 9.81], dtype=np.float32),
        np.zeros(3, dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
    )


class TestNoisePerformance:
    """Benchmark sensor noise application throughput."""

    def test_lidar_noise(self, benchmark, noise_model, lidar_ranges):
        benchmark(noise_model.apply_lidar, lidar_ranges)

    def test_camera_noise(self, benchmark, noise_model, camera_image):
        benchmark(noise_model.apply_camera, camera_image)

    def test_imu_noise(self, benchmark, noise_model, imu_data):
        accel, gyro, ori = imu_data
        benchmark(noise_model.apply_imu, accel, gyro, ori)

    def test_odometry_noise(self, benchmark, noise_model):
        pose = np.array([1.0, 2.0, 0.5], dtype=np.float32)
        benchmark(noise_model.apply_odometry, pose)

    def test_encoder_noise(self, benchmark, noise_model):
        speeds = np.array([100.0, 100.0, 100.0, 100.0], dtype=np.float32)
        benchmark(noise_model.apply_encoder, speeds)

    def test_current_noise(self, benchmark, noise_model):
        current = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        benchmark(noise_model.apply_current, current)


class TestDomainRandomizationPerformance:
    """Benchmark domain randomization sampling."""

    def test_sample(self, benchmark):
        dr = DomainRandomization(seed=42)
        benchmark(dr.sample)


class TestMockBackendPerformance:
    """Benchmark MockBackend operations as a proxy for control loop budget."""

    @pytest.fixture()
    def backend(self):
        from threewe.backends.mock import MockBackend
        from threewe.config import load_config

        config = load_config("standard_v2")
        b = MockBackend(config, scene="office_v2")
        b.connect()
        yield b
        b.disconnect()

    def test_get_camera_image(self, benchmark, backend):
        benchmark(backend.get_camera_image)

    def test_get_lidar_scan(self, benchmark, backend):
        benchmark(backend.get_lidar_scan)

    def test_get_pose(self, benchmark, backend):
        benchmark(backend.get_pose)

    def test_set_velocity(self, benchmark, backend):
        benchmark(backend.set_velocity, 0.5, 0.0, 0.1)

    def test_sensor_read_cycle(self, benchmark, backend):
        """Full sensor read cycle: image + lidar + pose + velocity."""

        def _cycle():
            backend.get_camera_image()
            backend.get_lidar_scan()
            backend.get_pose()
            backend.get_velocity()

        benchmark(_cycle)
