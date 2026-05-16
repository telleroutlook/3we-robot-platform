# SPDX-License-Identifier: Apache-2.0
"""Gymnasium environments for the 3we robot platform.

NavigationEnv: Point-to-point navigation with obstacle avoidance.
ExplorationEnv: Coverage-based autonomous exploration.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False


class ActionLevel(Enum):
    """Multi-level action space for different research needs.

    CMD_VEL: (3,) normalized [vx, vy, omega] — default, end-to-end RL.
    WHEEL_VEL: (4,) individual wheel target speeds (RPM) — low-level control research.
    WAYPOINT: (3,) local target point [x, y, theta] — high-level VLM/LLM planning.
    """

    CMD_VEL = "cmd_vel"
    WHEEL_VEL = "wheel_vel"
    WAYPOINT = "waypoint"


def _check_gym_available() -> None:
    if not GYM_AVAILABLE:
        raise ImportError(
            "gymnasium is required for threewe gym environments. "
            "Install with: pip install threewe[sim]"
        )


def _low_level_info(velocity: np.ndarray, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Generate simulated low-level physics data for info dict.

    Provides wheel_speeds, imu_raw, motor_current, and cmd_vel_raw
    with realistic noise for Domain Randomization research.
    """
    vx, vy, omega = velocity[0], velocity[1], velocity[2]
    wheel_radius = 0.0325
    k = 0.17  # wheel_base_x + wheel_base_y
    speeds_rad = np.array(
        [
            (vx - vy - k * omega) / wheel_radius,
            (vx + vy + k * omega) / wheel_radius,
            (vx + vy - k * omega) / wheel_radius,
            (vx - vy + k * omega) / wheel_radius,
        ],
        dtype=np.float32,
    )
    wheel_speeds = speeds_rad * 60.0 / (2.0 * np.pi)
    wheel_speeds += rng.normal(0.0, 2.0, size=(4,)).astype(np.float32)

    imu_raw = np.array(
        [
            rng.normal(0.0, 0.01),
            rng.normal(0.0, 0.01),
            9.81 + rng.normal(0.0, 0.01),
            rng.normal(0.0, 0.0014),
            rng.normal(0.0, 0.0014),
            omega + rng.normal(0.0, 0.0014),
        ],
        dtype=np.float32,
    )

    base_current = 0.05 + np.abs(wheel_speeds) * 0.003
    motor_current = np.maximum(base_current + rng.normal(0.0, 0.015, size=(4,)), 0.0).astype(
        np.float32
    )

    cmd_vel_raw = velocity.copy()

    return {
        "wheel_speeds": wheel_speeds,
        "imu_raw": imu_raw,
        "motor_current": motor_current,
        "cmd_vel_raw": cmd_vel_raw,
    }


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
        action_level: ActionLevel = ActionLevel.CMD_VEL,
    ) -> None:
        _check_gym_available()
        super().__init__()

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.goal_threshold = goal_threshold
        self.image_size = image_size
        self.lidar_points = lidar_points
        self.arena_size = arena_size
        self.action_level = action_level

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

        if action_level == ActionLevel.WHEEL_VEL:
            self.action_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        elif action_level == ActionLevel.WAYPOINT:
            self.action_space = spaces.Box(
                low=np.array([-arena_size, -arena_size, -np.pi], dtype=np.float32),
                high=np.array([arena_size, arena_size, np.pi], dtype=np.float32),
            )
        else:
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

    def _action_to_velocity(self, action: np.ndarray) -> tuple[float, float, float]:
        """Convert action to (vx, vy, omega) based on configured action_level."""
        if self.action_level == ActionLevel.WHEEL_VEL:
            action = np.clip(action, -1.0, 1.0).astype(np.float32)
            wheel_radius = 0.0325
            k = 0.17
            max_rpm = 200.0
            rpms = action * max_rpm
            rad_s = rpms * (2.0 * np.pi) / 60.0
            vx = float(wheel_radius * (rad_s[0] + rad_s[1] + rad_s[2] + rad_s[3]) / 4.0)
            vy = float(wheel_radius * (-rad_s[0] + rad_s[1] + rad_s[2] - rad_s[3]) / 4.0)
            omega = float(wheel_radius * (-rad_s[0] + rad_s[1] - rad_s[2] + rad_s[3]) / (4.0 * k))
            return vx, vy, omega
        elif self.action_level == ActionLevel.WAYPOINT:
            target_x = float(action[0])
            target_y = float(action[1])
            dx = target_x - self._pose[0]
            dy = target_y - self._pose[1]
            dist = np.sqrt(dx * dx + dy * dy)
            if dist < 0.05:
                return 0.0, 0.0, 0.0
            heading = np.arctan2(dy, dx)
            angle_diff = heading - self._pose[2]
            angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi
            omega = float(np.clip(angle_diff * 2.0, -1.0, 1.0))
            vx = float(np.clip(dist * 0.5, 0.0, 0.5)) if abs(angle_diff) < 0.5 else 0.0
            return vx, 0.0, omega
        else:
            action = np.clip(action, -1.0, 1.0).astype(np.float32)
            return float(action[0] * 0.5), float(action[1] * 0.3), float(action[2] * 1.0)

    def step(
        self, action: np.ndarray
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
        self._step_count += 1
        vx, vy, omega = self._action_to_velocity(action)

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

        info = {"distance": distance}
        info.update(_low_level_info(self._velocity, self.np_random))
        return self._get_obs(), float(reward), terminated, truncated, info

    def _distance_to_goal(self) -> float:
        dx = self._goal[0] - self._pose[0]
        dy = self._goal[1] - self._pose[1]
        return float(np.sqrt(dx * dx + dy * dy))

    def _get_obs(self) -> dict[str, np.ndarray]:
        """Placeholder: returns zero image and max-range lidar.

        Hook into a real backend for Sim2Real transfer.
        """
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
        info.update(_low_level_info(self._velocity, self.np_random))
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
        """Placeholder: returns zero image and max-range lidar.

        Hook into a real backend for Sim2Real transfer.
        """
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


OBJECT_CATEGORIES = [
    "chair",
    "table",
    "door",
    "couch",
    "bed",
    "toilet",
    "tv",
    "refrigerator",
    "sink",
    "plant",
]


class ObjectNavEnv(gym.Env if GYM_AVAILABLE else object):  # type: ignore[misc]
    """Object-goal navigation: navigate to an object by category name.

    Observation space (Dict):
        - image: (64, 64, 3) uint8 RGB
        - lidar: (360,) float32, meters
        - pose: (3,) float32 [x, y, theta]
        - velocity: (3,) float32 [vx, vy, omega]
        - object_goal: (10,) float32 one-hot encoding of target category

    Action space (Box):
        - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

    Reward:
        - Distance reduction toward object
        - Object reached bonus
        - Collision penalty
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        render_mode: str | None = None,
        max_steps: int = 500,
        goal_threshold: float = 0.3,
        image_size: tuple[int, int] = (64, 64),
        lidar_points: int = 360,
        arena_size: float = 5.0,
        num_objects: int = 5,
    ) -> None:
        _check_gym_available()
        super().__init__()

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.goal_threshold = goal_threshold
        self.image_size = image_size
        self.lidar_points = lidar_points
        self.arena_size = arena_size
        self.num_objects = num_objects
        self.num_categories = len(OBJECT_CATEGORIES)

        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(
                    0, 255, shape=(image_size[1], image_size[0], 3), dtype=np.uint8
                ),
                "lidar": spaces.Box(0.0, 12.0, shape=(lidar_points,), dtype=np.float32),
                "pose": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
                "velocity": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
                "object_goal": spaces.Box(0.0, 1.0, shape=(self.num_categories,), dtype=np.float32),
            }
        )

        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._object_positions: np.ndarray = np.zeros((num_objects, 2), dtype=np.float32)
        self._object_categories: list[int] = []
        self._target_category: int = 0
        self._step_count = 0
        self._prev_distance = 0.0

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._step_count = 0

        self._object_positions = self.np_random.uniform(
            -self.arena_size * 0.8, self.arena_size * 0.8, size=(self.num_objects, 2)
        ).astype(np.float32)
        self._object_categories = [
            int(self.np_random.integers(0, self.num_categories)) for _ in range(self.num_objects)
        ]
        self._target_category = self._object_categories[
            int(self.np_random.integers(0, self.num_objects))
        ]
        self._prev_distance = self._distance_to_nearest_target()

        info = {"target_object": OBJECT_CATEGORIES[self._target_category]}
        return self._get_obs(), info

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

        distance = self._distance_to_nearest_target()
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

        info = {
            "distance": distance,
            "target_object": OBJECT_CATEGORIES[self._target_category],
        }
        info.update(_low_level_info(self._velocity, self.np_random))
        return self._get_obs(), float(reward), terminated, truncated, info

    def _distance_to_nearest_target(self) -> float:
        min_dist = float("inf")
        for i, cat in enumerate(self._object_categories):
            if cat == self._target_category:
                dx = self._object_positions[i, 0] - self._pose[0]
                dy = self._object_positions[i, 1] - self._pose[1]
                dist = float(np.sqrt(dx * dx + dy * dy))
                min_dist = min(min_dist, dist)
        return min_dist if min_dist != float("inf") else 0.0

    def _get_obs(self) -> dict[str, np.ndarray]:
        """Placeholder: returns zero image and max-range lidar.

        Hook into a real backend for Sim2Real transfer.
        """
        goal_onehot = np.zeros(self.num_categories, dtype=np.float32)
        goal_onehot[self._target_category] = 1.0
        return {
            "image": np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8),
            "lidar": np.full(self.lidar_points, 12.0, dtype=np.float32),
            "pose": self._pose.copy(),
            "velocity": self._velocity.copy(),
            "object_goal": goal_onehot,
        }

    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            return self._get_obs()["image"]
        return None


class VLNEnv(gym.Env if GYM_AVAILABLE else object):  # type: ignore[misc]
    """Vision-Language Navigation: follow a natural language instruction.

    Observation space (Dict):
        - image: (64, 64, 3) uint8 RGB
        - lidar: (360,) float32, meters
        - pose: (3,) float32 [x, y, theta]
        - velocity: (3,) float32 [vx, vy, omega]
        - instruction_embedding: (64,) float32 encoded instruction

    Action space (Box):
        - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

    The environment simulates waypoint-following for language instructions.
    A pre-defined path of waypoints represents the instruction trajectory;
    reward is based on progress along the path.
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        render_mode: str | None = None,
        max_steps: int = 500,
        waypoint_threshold: float = 0.3,
        image_size: tuple[int, int] = (64, 64),
        lidar_points: int = 360,
        arena_size: float = 5.0,
        num_waypoints: int = 4,
        embedding_dim: int = 64,
    ) -> None:
        _check_gym_available()
        super().__init__()

        self.render_mode = render_mode
        self.max_steps = max_steps
        self.waypoint_threshold = waypoint_threshold
        self.image_size = image_size
        self.lidar_points = lidar_points
        self.arena_size = arena_size
        self.num_waypoints = num_waypoints
        self.embedding_dim = embedding_dim

        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(
                    0, 255, shape=(image_size[1], image_size[0], 3), dtype=np.uint8
                ),
                "lidar": spaces.Box(0.0, 12.0, shape=(lidar_points,), dtype=np.float32),
                "pose": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
                "velocity": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
                "instruction_embedding": spaces.Box(
                    -1.0, 1.0, shape=(embedding_dim,), dtype=np.float32
                ),
            }
        )

        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._waypoints: np.ndarray = np.zeros((num_waypoints, 2), dtype=np.float32)
        self._instruction_embedding = np.zeros(embedding_dim, dtype=np.float32)
        self._current_waypoint_idx = 0
        self._step_count = 0
        self._prev_distance = 0.0

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)

        self._pose = np.zeros(3, dtype=np.float32)
        self._velocity = np.zeros(3, dtype=np.float32)
        self._step_count = 0
        self._current_waypoint_idx = 0

        points = [np.zeros(2, dtype=np.float32)]
        for _ in range(self.num_waypoints):
            prev = points[-1]
            offset = self.np_random.uniform(-1.5, 1.5, size=(2,)).astype(np.float32)
            next_pt = np.clip(prev + offset, -self.arena_size * 0.8, self.arena_size * 0.8)
            points.append(next_pt)
        self._waypoints = np.array(points[1:], dtype=np.float32)

        self._instruction_embedding = self.np_random.uniform(
            -1.0, 1.0, size=(self.embedding_dim,)
        ).astype(np.float32)

        self._prev_distance = self._distance_to_current_waypoint()

        return self._get_obs(), {"waypoints_remaining": self.num_waypoints}

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

        distance = self._distance_to_current_waypoint()
        reward = (self._prev_distance - distance) * 5.0
        self._prev_distance = distance

        terminated = False
        if distance < self.waypoint_threshold:
            reward += 20.0
            self._current_waypoint_idx += 1
            if self._current_waypoint_idx >= self.num_waypoints:
                reward += 100.0
                terminated = True
            else:
                self._prev_distance = self._distance_to_current_waypoint()

        if abs(self._pose[0]) > self.arena_size or abs(self._pose[1]) > self.arena_size:
            reward -= 50.0
            terminated = True

        truncated = self._step_count >= self.max_steps

        info = {
            "waypoints_remaining": self.num_waypoints - self._current_waypoint_idx,
            "distance": distance,
        }
        info.update(_low_level_info(self._velocity, self.np_random))
        return self._get_obs(), float(reward), terminated, truncated, info

    def _distance_to_current_waypoint(self) -> float:
        if self._current_waypoint_idx >= self.num_waypoints:
            return 0.0
        wp = self._waypoints[self._current_waypoint_idx]
        dx = wp[0] - self._pose[0]
        dy = wp[1] - self._pose[1]
        return float(np.sqrt(dx * dx + dy * dy))

    def _get_obs(self) -> dict[str, np.ndarray]:
        """Placeholder: returns zero image, max-range lidar, and random instruction embedding."""
        return {
            "image": np.zeros((self.image_size[1], self.image_size[0], 3), dtype=np.uint8),
            "lidar": np.full(self.lidar_points, 12.0, dtype=np.float32),
            "pose": self._pose.copy(),
            "velocity": self._velocity.copy(),
            "instruction_embedding": self._instruction_embedding.copy(),
        }

    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            return self._get_obs()["image"]
        return None
