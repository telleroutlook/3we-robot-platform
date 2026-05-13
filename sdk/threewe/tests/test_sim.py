# SPDX-License-Identifier: Apache-2.0
"""Tests for sim module: sensor noise and domain randomization."""

from __future__ import annotations

import numpy as np
import pytest

from threewe.sim.domain_randomization import DomainRandomization
from threewe.sim.noise import SensorNoiseModel


class TestSensorNoiseModel:
    def test_default_construction(self):
        noise = SensorNoiseModel()
        assert noise.lidar.distance_stddev == 0.008
        assert noise.imu.gyro_stddev == 0.0014
        assert noise.camera.pixel_stddev == 3.0
        assert noise.odometry.slip_factor_min == 0.05

    def test_apply_lidar(self):
        noise = SensorNoiseModel(seed=42)
        ranges = np.ones(360, dtype=np.float32) * 5.0
        noisy = noise.apply_lidar(ranges)

        assert noisy.shape == (360,)
        assert noisy.dtype == np.float32
        assert not np.array_equal(noisy, ranges)
        assert np.all(noisy >= 0.0)
        assert np.all(noisy <= 12.0)

    def test_apply_lidar_preserves_shape(self):
        noise = SensorNoiseModel(seed=1)
        ranges = np.ones(720, dtype=np.float32) * 3.0
        noisy = noise.apply_lidar(ranges)
        assert noisy.shape == (720,)

    def test_apply_imu(self):
        noise = SensorNoiseModel(seed=42)
        accel = np.array([0.0, 0.0, 9.81], dtype=np.float32)
        gyro = np.zeros(3, dtype=np.float32)
        ori = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

        noisy_accel, noisy_gyro, noisy_ori = noise.apply_imu(accel, gyro, ori)

        assert noisy_accel.shape == (3,)
        assert noisy_gyro.shape == (3,)
        assert noisy_ori.shape == (4,)
        assert abs(np.linalg.norm(noisy_ori) - 1.0) < 1e-5

    def test_apply_camera(self):
        noise = SensorNoiseModel(seed=42)
        image = np.full((64, 64, 3), 128, dtype=np.uint8)
        noisy = noise.apply_camera(image)

        assert noisy.shape == (64, 64, 3)
        assert noisy.dtype == np.uint8
        assert not np.array_equal(noisy, image)

    def test_apply_camera_clamps(self):
        noise = SensorNoiseModel(seed=42)
        image = np.full((32, 32, 3), 250, dtype=np.uint8)
        noisy = noise.apply_camera(image)
        assert np.all(noisy <= 255)
        assert np.all(noisy >= 0)

    def test_apply_odometry(self):
        noise = SensorNoiseModel(seed=42)
        pose = np.array([1.0, 2.0, 0.5], dtype=np.float32)
        noisy = noise.apply_odometry(pose)

        assert noisy.shape == (3,)
        assert not np.array_equal(noisy, pose)

    def test_seed_reproducibility(self):
        noise = SensorNoiseModel(seed=123)
        ranges = np.ones(100, dtype=np.float32) * 4.0
        noisy1 = noise.apply_lidar(ranges)
        noisy2 = noise.apply_lidar(ranges)
        np.testing.assert_array_equal(noisy1, noisy2)


class TestDomainRandomization:
    def test_default_construction(self):
        dr = DomainRandomization()
        assert dr.physics.mass_scale_range == (0.9, 1.1)
        assert dr.visual.randomize_textures is True

    def test_sample_returns_dict(self):
        dr = DomainRandomization(seed=42)
        params = dr.sample()

        assert "mass_scale" in params
        assert "friction_scale" in params
        assert "lighting_intensity" in params
        assert "lidar_noise_scale" in params

    def test_sample_values_in_range(self):
        dr = DomainRandomization(seed=42)
        params = dr.sample()

        assert 0.9 <= params["mass_scale"] <= 1.1
        assert 0.8 <= params["friction_scale"] <= 1.2
        assert 0.5 <= params["lighting_intensity"] <= 1.5
        assert 0.5 <= params["lidar_noise_scale"] <= 2.0

    def test_from_yaml(self, tmp_path):
        yaml = pytest.importorskip("yaml")

        config = {
            "physics": {
                "mass_scale_range": [0.85, 1.15],
                "friction_scale_range": [0.7, 1.3],
                "motor_torque_noise_stddev": 0.08,
            },
            "visual": {
                "randomize_textures": False,
                "lighting_intensity_range": [0.3, 2.0],
            },
            "sensor": {
                "lidar_noise_scale_range": [1.0, 3.0],
            },
            "seed": 99,
        }

        path = tmp_path / "dr_config.yaml"
        path.write_text(yaml.dump(config))

        dr = DomainRandomization.from_yaml(path)
        assert dr.physics.mass_scale_range == (0.85, 1.15)
        assert dr.visual.randomize_textures is False
        assert dr.sensor.lidar_noise_scale_range == (1.0, 3.0)
        assert dr.seed == 99

    def test_sample_reproducibility(self):
        dr = DomainRandomization(seed=42)
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        params1 = dr.sample(rng=rng1)
        params2 = dr.sample(rng=rng2)
        assert params1 == params2


class TestNoisyObservationWrapper:
    def test_wrapper_applies_noise(self):
        pytest.importorskip("gymnasium")
        import gymnasium

        from threewe.gym.wrappers import NoisyObservation

        env = gymnasium.make("3we/Navigation-v1")
        wrapped = NoisyObservation(env, seed=42)

        obs, _ = wrapped.reset(seed=10)
        assert "lidar" in obs
        assert "image" in obs
        assert obs["lidar"].shape == (360,)
        wrapped.close()

    def test_wrapper_modifies_lidar(self):
        pytest.importorskip("gymnasium")
        import gymnasium

        from threewe.gym.wrappers import NoisyObservation

        env = gymnasium.make("3we/Navigation-v1")
        wrapped = NoisyObservation(env, seed=42)

        obs_wrapped, _ = wrapped.reset(seed=10)
        wrapped.close()

        env2 = gymnasium.make("3we/Navigation-v1")
        obs_clean, _ = env2.reset(seed=10)
        env2.close()

        assert not np.array_equal(obs_wrapped["lidar"], obs_clean["lidar"])
