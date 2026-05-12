# SPDX-License-Identifier: Apache-2.0
"""Gymnasium environments for the 3we robot platform.

NavigationEnv: Point-to-point navigation with obstacle avoidance.
ExplorationEnv: Coverage-based autonomous exploration.
"""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False


def _check_gym_available() -> None:
    if not GYM_AVAILABLE:
        raise ImportError(
            "gymnasium is required for threewe gym environments. "
            "Install with: pip install threewe[sim]"
        )


class NavigationEnv(gym.Env if GYM_AVAILABLE else object):  # type: ignore[misc]
    """Point-to-point navigation environment.

    Observation space (Dict):
        - image: (64, 64, 3) uint8 RGB
        - lidar: (360,) float32, meters
        - pose: (3,) float32 [x, y, theta]
        - velocity: (3,) float32 [vx, vy, omega]
        - goal: (2,) float32 [gx, gy]

    Action space (Box):
        - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

    Reward:
        - Distance reduction toward goal
        - Collision penalty
        - Goal reached bonus
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        render_mode: str | None = None,
        max_steps: int = 500,
        goal_threshold: float = 0.2,
        image_size: tuple[int, int] = (64, 64),
        lidar_points: int = 360,
        arena_size: float = 5.0,
    ) -> None:
        _check_gym_available()
        super().__init__()

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.goal_threshold = goal_threshold
        self.image_size = image_size
        self.lidar_points = lidar_points
        self.arena_size = arena_size

        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(
                    0, 255, shape=(image_size[1], image_size[0], 3), dtype=np.uint8
                ),
                "lidar": spaces.Box(0.0, 12.0, shape=(lidar_points,), dtype=np.float32),
                "pose": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
                "velocity": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
                "goal": spaces.Box(-arena_size, arena_size, shape=(2,), dtype=np.float32),
            }
        )

        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._goal = np.zeros(2, dtype=np.float32)
        self._step_count = 0
        self._prev_distance = 0.0

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._goal = self.np_random.uniform(
            -self.arena_size * 0.8, self.arena_size * 0.8, size=(2,)
        ).astype(np.float32)
        self._step_count = 0
        self._prev_distance = self._distance_to_goal()

        return self._get_obs(), {}

    def step(
        self, action: np.ndarray
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
        action = np.clip(action, -1.0, 1.0).astype(np.float32)
        self._step_count += 1

        vx = action[0] * 0.5
        vy = action[1] * 0.3
        omega = action[2] * 1.0

        dt = 0.1
        cos_t = np.cos(self._pose[2])
        sin_t = np.sin(self._pose[2])
        self._pose[0] += (vx * cos_t - vy * sin_t) * dt
        self._pose[1] += (vx * sin_t + vy * cos_t) * dt
        self._pose[2] += omega * dt
        self._velocity = np.array([vx, vy, omega], dtype=np.float32)

        distance = self._distance_to_goal()
        reward = (self._prev_distance - distance) * 10.0
        self._prev_distance = distance

        terminated = False
        if distance < self.goal_threshold:
            reward += 100.0
            terminated = True

        if abs(self._pose[0]) > self.arena_size or abs(self._pose[1]) > self.arena_size:
            reward -= 50.0
            terminated = True

        truncated = self._step_count >= self.max_steps

        return self._get_obs(), float(reward), terminated, truncated, {"distance": distance}

    def _distance_to_goal(self) -> float:
        dx = self._goal[0] - self._pose[0]
        dy = self._goal[1] - self._pose[1]
        return float(np.sqrt(dx * dx + dy * dy))

    def _get_obs(self) -> dict[str, np.ndarray]:
        return {
            "image": np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8),
            "lidar": np.full(self.lidar_points, 12.0, dtype=np.float32),
            "pose": self._pose.copy(),
            "velocity": self._velocity.copy(),
            "goal": self._goal.copy(),
        }

    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            return self._get_obs()["image"]
        return None


class ExplorationEnv(gym.Env if GYM_AVAILABLE else object):  # type: ignore[misc]
    """Coverage-based exploration environment.

    Observation space (Dict):
        - image: (64, 64, 3) uint8 RGB
        - lidar: (360,) float32, meters
        - pose: (3,) float32 [x, y, theta]
        - velocity: (3,) float32 [vx, vy, omega]
        - coverage_map: (64, 64) float32, 0=unexplored, 1=explored

    Action space (Box):
        - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

    Reward:
        - New cells explored
        - Collision penalty
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        render_mode: str | None = None,
        max_steps: int = 1000,
        map_size: int = 64,
        image_size: tuple[int, int] = (64, 64),
        lidar_points: int = 360,
        arena_size: float = 5.0,
    ) -> None:
        _check_gym_available()
        super().__init__()

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.map_size = map_size
        self.image_size = image_size
        self.lidar_points = lidar_points
        self.arena_size = arena_size
        self._resolution = (2.0 * arena_size) / map_size

        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(
                    0, 255, shape=(image_size[1], image_size[0], 3), dtype=np.uint8
                ),
                "lidar": spaces.Box(0.0, 12.0, shape=(lidar_points,), dtype=np.float32),
                "pose": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
                "velocity": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
                "coverage_map": spaces.Box(0.0, 1.0, shape=(map_size, map_size), dtype=np.float32),
            }
        )

        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._coverage = np.zeros((map_size, map_size), dtype=np.float32)
        self._step_count = 0

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._coverage = np.zeros((self.map_size, self.map_size), dtype=np.float32)
        self._step_count = 0
        self._mark_explored()

        return self._get_obs(), {}

    def step(
        self, action: np.ndarray
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
        action = np.clip(action, -1.0, 1.0).astype(np.float32)
        self._step_count += 1

        prev_explored = float(np.sum(self._coverage > 0))

        vx = action[0] * 0.5
        vy = action[1] * 0.3
        omega = action[2] * 1.0

        dt = 0.1
        cos_t = np.cos(self._pose[2])
        sin_t = np.sin(self._pose[2])
        self._pose[0] += (vx * cos_t - vy * sin_t) * dt
        self._pose[1] += (vx * sin_t + vy * cos_t) * dt
        self._pose[2] += omega * dt
        self._velocity = np.array([vx, vy, omega], dtype=np.float32)

        terminated = False
        if abs(self._pose[0]) > self.arena_size or abs(self._pose[1]) > self.arena_size:
            self._pose[0] = np.clip(self._pose[0], -self.arena_size, self.arena_size)
            self._pose[1] = np.clip(self._pose[1], -self.arena_size, self.arena_size)

        self._mark_explored()
        new_explored = float(np.sum(self._coverage > 0))
        reward = (new_explored - prev_explored) * 1.0

        total_cells = self.map_size * self.map_size
        coverage_ratio = new_explored / total_cells
        if coverage_ratio >= 0.95:
            reward += 100.0
            terminated = True

        truncated = self._step_count >= self.max_steps

        info = {"coverage": coverage_ratio, "cells_explored": int(new_explored)}
        return self._get_obs(), float(reward), terminated, truncated, info

    def _mark_explored(self) -> None:
        cx = int((self._pose[0] + self.arena_size) / self._resolution)
        cy = int((self._pose[1] + self.arena_size) / self._resolution)
        radius = 3
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.map_size and 0 <= ny < self.map_size:
                    self._coverage[ny, nx] = 1.0

    def _get_obs(self) -> dict[str, np.ndarray]:
        return {
            "image": np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8),
            "lidar": np.full(self.lidar_points, 12.0, dtype=np.float32),
            "pose": self._pose.copy(),
            "velocity": self._velocity.copy(),
            "coverage_map": self._coverage.copy(),
        }

    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            return (self._coverage * 255).astype(np.uint8)
        return None
