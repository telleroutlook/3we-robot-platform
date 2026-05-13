# SPDX-License-Identifier: Apache-2.0
"""Multi-agent cooperative exploration environment.

Implements a PettingZoo-compatible parallel API for multi-robot RL.
2-4 robots share a coverage map and must cooperate to maximize exploration.
"""

from __future__ import annotations

import numpy as np

try:
    import gymnasium  # noqa: F401
    from gymnasium import spaces

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False


class MultiAgentEnv:
    """Multi-agent cooperative exploration environment.

    Compatible with PettingZoo parallel API:
        observations, infos = env.reset()
        while env.agents:
            actions = {agent: policy(obs) for agent, obs in observations.items()}
            observations, rewards, terminations, truncations, infos = env.step(actions)

    Observation per agent (Dict):
        - image: (64, 64, 3) uint8 RGB
        - lidar: (360,) float32
        - pose: (3,) float32 [x, y, theta]
        - other_poses: (num_agents-1, 3) float32
        - coverage_map: (50, 50) float32 shared coverage

    Action per agent (Box):
        - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

    Reward:
        - Team coverage gain (shared)
        - Inter-agent collision penalty
        - Exploration bonus for visiting new cells
    """

    metadata = {"render_modes": ["human", "rgb_array"], "name": "multiagent_exploration_v1"}

    def __init__(
        self,
        num_agents: int = 2,
        arena_size: float = 10.0,
        max_steps: int = 500,
        coverage_resolution: int = 50,
        collision_radius: float = 0.4,
        render_mode: str | None = None,
    ) -> None:
        if not GYM_AVAILABLE:
            raise ImportError(
                "gymnasium is required for threewe gym environments. "
                "Install with: pip install threewe[sim]"
            )

        assert 2 <= num_agents <= 4, "num_agents must be between 2 and 4"

        self._num_agents = num_agents
        self._arena_size = arena_size
        self._max_steps = max_steps
        self._coverage_resolution = coverage_resolution
        self._collision_radius = collision_radius
        self.render_mode = render_mode

        self.possible_agents = [f"robot_{i}" for i in range(num_agents)]
        self.agents: list[str] = []

        self._observation_space = spaces.Dict(
            {
                "image": spaces.Box(0, 255, shape=(64, 64, 3), dtype=np.uint8),
                "lidar": spaces.Box(0, 12.0, shape=(360,), dtype=np.float32),
                "pose": spaces.Box(-arena_size, arena_size, shape=(3,), dtype=np.float32),
                "other_poses": spaces.Box(
                    -arena_size, arena_size, shape=(num_agents - 1, 3), dtype=np.float32
                ),
                "coverage_map": spaces.Box(
                    0.0, 1.0, shape=(coverage_resolution, coverage_resolution), dtype=np.float32
                ),
            }
        )
        self._action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)

        self._poses: dict[str, np.ndarray] = {}
        self._coverage_map = np.zeros((coverage_resolution, coverage_resolution), dtype=np.float32)
        self._step_count = 0

    @property
    def num_agents(self) -> int:
        return self._num_agents

    def observation_space(self, agent: str) -> spaces.Dict:
        return self._observation_space

    def action_space(self, agent: str) -> spaces.Box:
        return self._action_space

    def reset(
        self, seed: int | None = None, options: dict | None = None
    ) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, dict]]:
        """Reset environment and return initial observations."""
        rng = np.random.default_rng(seed)

        self.agents = list(self.possible_agents)
        self._step_count = 0
        self._coverage_map = np.zeros(
            (self._coverage_resolution, self._coverage_resolution), dtype=np.float32
        )

        for i, agent in enumerate(self.agents):
            angle = 2 * np.pi * i / self._num_agents
            x = self._arena_size * 0.3 * np.cos(angle)
            y = self._arena_size * 0.3 * np.sin(angle)
            theta = float(rng.uniform(-np.pi, np.pi))
            self._poses[agent] = np.array([x, y, theta], dtype=np.float32)

        self._update_coverage()

        observations = {agent: self._get_obs(agent) for agent in self.agents}
        infos: dict[str, dict] = {agent: {} for agent in self.agents}
        return observations, infos

    def step(
        self, actions: dict[str, np.ndarray]
    ) -> tuple[
        dict[str, dict[str, np.ndarray]],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict],
    ]:
        """Step all agents simultaneously."""
        self._step_count += 1
        prev_coverage = float(self._coverage_map.sum())

        for agent, action in actions.items():
            if agent not in self.agents:
                continue
            action = np.clip(action, -1.0, 1.0)
            vx, vy, omega = action * np.array([0.5, 0.5, 1.0])
            dt = 0.1
            pose = self._poses[agent]
            cos_t, sin_t = np.cos(pose[2]), np.sin(pose[2])
            pose[0] += (vx * cos_t - vy * sin_t) * dt
            pose[1] += (vx * sin_t + vy * cos_t) * dt
            pose[2] += omega * dt
            pose[0] = np.clip(pose[0], -self._arena_size * 0.9, self._arena_size * 0.9)
            pose[1] = np.clip(pose[1], -self._arena_size * 0.9, self._arena_size * 0.9)

        self._update_coverage()
        new_coverage = float(self._coverage_map.sum())
        coverage_gain = new_coverage - prev_coverage

        collision_penalties = self._compute_collisions()

        rewards: dict[str, float] = {}
        for agent in self.agents:
            rewards[agent] = coverage_gain * 10.0 - collision_penalties.get(agent, 0.0)

        truncated = self._step_count >= self._max_steps
        terminations = {agent: False for agent in self.agents}
        truncations = {agent: truncated for agent in self.agents}

        if truncated:
            self.agents = []

        observations = {
            agent: self._get_obs(agent) for agent in self.possible_agents if agent in actions
        }
        infos: dict[str, dict] = {
            agent: {"coverage": float(self._coverage_map.mean())} for agent in observations
        }

        return observations, rewards, terminations, truncations, infos

    def _get_obs(self, agent: str) -> dict[str, np.ndarray]:
        pose = self._poses[agent]
        other_poses = np.array(
            [self._poses[a] for a in self.agents if a != agent], dtype=np.float32
        )
        if len(other_poses) == 0:
            other_poses = np.zeros((self._num_agents - 1, 3), dtype=np.float32)

        return {
            "image": np.zeros((64, 64, 3), dtype=np.uint8),
            "lidar": np.full(360, 10.0, dtype=np.float32),
            "pose": pose.copy(),
            "other_poses": other_poses,
            "coverage_map": self._coverage_map.copy(),
        }

    def _update_coverage(self) -> None:
        """Mark cells around each agent as explored."""
        res = self._coverage_resolution
        cell_size = (2 * self._arena_size) / res
        radius_cells = max(1, int(1.5 / cell_size))

        for agent in self.agents:
            pose = self._poses[agent]
            cx = int((pose[0] + self._arena_size) / cell_size)
            cy = int((pose[1] + self._arena_size) / cell_size)
            for dx in range(-radius_cells, radius_cells + 1):
                for dy in range(-radius_cells, radius_cells + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < res and 0 <= ny < res:
                        self._coverage_map[ny, nx] = 1.0

    def _compute_collisions(self) -> dict[str, float]:
        """Check inter-agent collisions and return penalties."""
        penalties: dict[str, float] = {}
        agents_list = list(self.agents)
        for i in range(len(agents_list)):
            for j in range(i + 1, len(agents_list)):
                a, b = agents_list[i], agents_list[j]
                dist = np.linalg.norm(self._poses[a][:2] - self._poses[b][:2])
                if dist < self._collision_radius:
                    penalties[a] = penalties.get(a, 0.0) + 5.0
                    penalties[b] = penalties.get(b, 0.0) + 5.0
        return penalties
