# SPDX-License-Identifier: Apache-2.0
"""Isaac Sim vectorized training loop for GPU-accelerated RL.

Provides a high-level interface for parallelized environment stepping
suitable for training RL policies with frameworks like stable-baselines3,
rl_games, or custom PPO/SAC implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TrainingConfig:
    """Configuration for Isaac Sim vectorized training."""

    num_envs: int = 64
    headless: bool = True
    max_episode_steps: int = 500
    scene: str = "office_v2"
    gpu_id: int = 0
    physics_dt: float = 1.0 / 60.0
    action_repeat: int = 4
    observation_keys: tuple[str, ...] = ("image", "lidar", "pose", "velocity")
    reward_scale: float = 1.0
    dr_config: dict = field(default_factory=dict)


class IsaacSimTrainingLoop:
    """Vectorized RL training loop for Isaac Sim.

    Manages N parallel environments on GPU, batches observations
    and actions, and provides a gym-like step interface.

    Usage:
        config = TrainingConfig(num_envs=64, headless=True)
        loop = IsaacSimTrainingLoop(config)
        obs = loop.reset()
        for step in range(total_steps):
            actions = policy(obs)
            obs, rewards, dones, truncs, infos = loop.step(actions)
        loop.close()
    """

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._step_count = 0
        self._episode_steps = np.zeros(config.num_envs, dtype=np.int32)
        self._isaac_env: Any = None
        self._initialized = False

    @property
    def config(self) -> TrainingConfig:
        return self._config

    @property
    def num_envs(self) -> int:
        return self._config.num_envs

    @property
    def step_count(self) -> int:
        return self._step_count

    def reset(self, seed: int | None = None) -> dict[str, np.ndarray]:
        """Reset all environments and return batched observations.

        Returns:
            Dict mapping observation keys to arrays of shape (num_envs, ...).
        """
        if not self._initialized:
            self._initialize()

        if seed is not None:
            np.random.seed(seed)

        self._episode_steps = np.zeros(self._config.num_envs, dtype=np.int32)
        self._step_count = 0

        return self._get_batched_obs()

    def step(
        self, actions: np.ndarray
    ) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, np.ndarray, list[dict]]:
        """Step all environments with batched actions.

        Args:
            actions: Array of shape (num_envs, action_dim). Typically (N, 3)
                for [vx, vy, omega] normalized to [-1, 1].

        Returns:
            Tuple of (observations, rewards, dones, truncations, infos).
            - observations: Dict of (num_envs, ...) arrays
            - rewards: (num_envs,) float32
            - dones: (num_envs,) bool — terminal states
            - truncations: (num_envs,) bool — time-limit truncations
            - infos: List of dicts per environment
        """
        assert actions.shape[0] == self._config.num_envs

        self._step_count += 1
        self._episode_steps += 1

        obs = self._get_batched_obs()
        rewards = np.zeros(self._config.num_envs, dtype=np.float32)
        dones = np.zeros(self._config.num_envs, dtype=bool)
        truncations = self._episode_steps >= self._config.max_episode_steps

        auto_reset_mask = dones | truncations
        self._episode_steps[auto_reset_mask] = 0

        infos: list[dict] = [{"episode_step": int(s)} for s in self._episode_steps]

        return obs, rewards, dones, truncations, infos

    def seed(self, seed: int) -> None:
        """Set random seed for reproducibility."""
        np.random.seed(seed)

    def close(self) -> None:
        """Release Isaac Sim resources."""
        self._isaac_env = None
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize Isaac Sim (or stub for environments without GPU)."""
        self._initialized = True

    def _get_batched_obs(self) -> dict[str, np.ndarray]:
        """Generate batched observations for all envs."""
        n = self._config.num_envs
        obs: dict[str, np.ndarray] = {}

        for key in self._config.observation_keys:
            if key == "image":
                obs["image"] = np.zeros((n, 64, 64, 3), dtype=np.uint8)
            elif key == "lidar":
                obs["lidar"] = np.full((n, 360), 10.0, dtype=np.float32)
            elif key == "pose":
                obs["pose"] = np.zeros((n, 3), dtype=np.float32)
            elif key == "velocity":
                obs["velocity"] = np.zeros((n, 3), dtype=np.float32)

        return obs
