# SPDX-License-Identifier: Apache-2.0
"""Tests for Gymnasium environments."""

import numpy as np
import pytest

try:
    import gymnasium

    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False


pytestmark = pytest.mark.skipif(not GYM_AVAILABLE, reason="gymnasium not installed")


class TestNavigationEnv:
    def setup_method(self):
        from threewe.gym.envs import NavigationEnv

        self.env = NavigationEnv(max_steps=50, arena_size=3.0)

    def teardown_method(self):
        self.env.close()

    def test_reset_returns_obs_and_info(self):
        obs, info = self.env.reset(seed=42)
        assert isinstance(obs, dict)
        assert isinstance(info, dict)

    def test_obs_space_keys(self):
        obs, _ = self.env.reset(seed=42)
        assert "image" in obs
        assert "lidar" in obs
        assert "pose" in obs
        assert "velocity" in obs
        assert "goal" in obs

    def test_obs_shapes(self):
        obs, _ = self.env.reset(seed=42)
        assert obs["image"].shape == (64, 64, 3)
        assert obs["lidar"].shape == (360,)
        assert obs["pose"].shape == (3,)
        assert obs["velocity"].shape == (3,)
        assert obs["goal"].shape == (2,)

    def test_step_returns_correct_tuple(self):
        self.env.reset(seed=42)
        action = np.array([0.5, 0.0, 0.0], dtype=np.float32)
        result = self.env.step(action)
        assert len(result) == 5
        obs, reward, terminated, truncated, info = result
        assert isinstance(obs, dict)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)

    def test_action_space_valid(self):
        assert self.env.action_space.shape == (3,)
        sample = self.env.action_space.sample()
        assert sample.shape == (3,)
        assert np.all(sample >= -1.0)
        assert np.all(sample <= 1.0)

    def test_truncation_at_max_steps(self):
        self.env.reset(seed=42)
        action = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        for _ in range(50):
            obs, reward, terminated, truncated, info = self.env.step(action)
            if terminated or truncated:
                break
        assert truncated is True

    def test_goal_reached_terminates(self):
        self.env.reset(seed=42)
        goal = self.env._goal
        action = np.zeros(3, dtype=np.float32)
        self.env._pose[0] = goal[0]
        self.env._pose[1] = goal[1]
        self.env._prev_distance = 0.0
        obs, reward, terminated, truncated, info = self.env.step(action)
        assert terminated is True

    def test_obs_in_observation_space(self):
        obs, _ = self.env.reset(seed=42)
        assert self.env.observation_space.contains(obs)


class TestExplorationEnv:
    def setup_method(self):
        from threewe.gym.envs import ExplorationEnv

        self.env = ExplorationEnv(max_steps=100, map_size=32, arena_size=3.0)

    def teardown_method(self):
        self.env.close()

    def test_reset_returns_obs(self):
        obs, info = self.env.reset(seed=42)
        assert "coverage_map" in obs
        assert obs["coverage_map"].shape == (32, 32)

    def test_exploration_increases_coverage(self):
        self.env.reset(seed=42)
        action = np.array([1.0, 0.0, 0.1], dtype=np.float32)
        total_explored = 0
        for _ in range(20):
            obs, reward, terminated, truncated, info = self.env.step(action)
            total_explored = info["cells_explored"]
            if terminated or truncated:
                break
        assert total_explored > 0

    def test_coverage_map_values_valid(self):
        obs, _ = self.env.reset(seed=42)
        coverage = obs["coverage_map"]
        assert np.all(coverage >= 0.0)
        assert np.all(coverage <= 1.0)

    def test_obs_in_observation_space(self):
        obs, _ = self.env.reset(seed=42)
        assert self.env.observation_space.contains(obs)


class TestGymRegistration:
    def test_navigation_env_registered(self):
        env = gymnasium.make("3we/Navigation-v1")
        obs, _ = env.reset()
        assert "image" in obs
        env.close()

    def test_exploration_env_registered(self):
        env = gymnasium.make("3we/Exploration-v1")
        obs, _ = env.reset()
        assert "coverage_map" in obs
        env.close()
