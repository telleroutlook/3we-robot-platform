# SPDX-License-Identifier: Apache-2.0
"""Gymnasium wrappers for domain randomization and sensor noise."""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import gymnasium as gym

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

from threewe.sim.noise import SensorNoiseModel


class NoisyObservation(gym.ObservationWrapper if GYM_AVAILABLE else object):  # type: ignore[misc]
    """Wrapper that applies sensor noise to observations.

    Adds calibrated noise to lidar, image, and pose observations
    to simulate real sensor characteristics during training.

    Usage:
        env = gymnasium.make("3we/Navigation-v1")
        env = NoisyObservation(env)
    """

    def __init__(
        self,
        env: gym.Env,
        noise_model: SensorNoiseModel | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(env)
        self._noise_model = noise_model or SensorNoiseModel(seed=seed)
        self._rng = np.random.default_rng(seed)

    def observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Apply noise to observation dict."""
        noisy_obs = dict(observation)

        if "lidar" in noisy_obs:
            noisy_obs["lidar"] = self._noise_model.apply_lidar(noisy_obs["lidar"], rng=self._rng)

        if "image" in noisy_obs:
            noisy_obs["image"] = self._noise_model.apply_camera(noisy_obs["image"], rng=self._rng)

        if "pose" in noisy_obs:
            noisy_obs["pose"] = self._noise_model.apply_odometry(noisy_obs["pose"], rng=self._rng)

        return noisy_obs
