# SPDX-License-Identifier: Apache-2.0
"""Tests for the MultiAgent environment."""

from __future__ import annotations

import numpy as np
import pytest

gymnasium = pytest.importorskip("gymnasium", reason="gymnasium required for multiagent tests")

from threewe.gym.multiagent import MultiAgentEnv  # noqa: E402


class TestMultiAgentEnvInit:
    def test_default_construction(self):
        env = MultiAgentEnv()
        assert env.num_agents == 2
        assert len(env.possible_agents) == 2

    def test_custom_agents(self):
        env = MultiAgentEnv(num_agents=4)
        assert env.num_agents == 4
        assert len(env.possible_agents) == 4
        assert env.possible_agents == ["robot_0", "robot_1", "robot_2", "robot_3"]

    def test_invalid_num_agents(self):
        with pytest.raises(AssertionError):
            MultiAgentEnv(num_agents=1)
        with pytest.raises(AssertionError):
            MultiAgentEnv(num_agents=5)


class TestMultiAgentEnvReset:
    def test_reset_returns_observations(self):
        env = MultiAgentEnv(num_agents=2)
        obs, infos = env.reset(seed=42)
        assert "robot_0" in obs
        assert "robot_1" in obs
        assert "robot_0" in infos

    def test_observation_spaces(self):
        env = MultiAgentEnv(num_agents=3)
        obs, _ = env.reset(seed=42)
        for agent in env.agents:
            o = obs[agent]
            assert o["image"].shape == (64, 64, 3)
            assert o["lidar"].shape == (360,)
            assert o["pose"].shape == (3,)
            assert o["other_poses"].shape == (2, 3)
            assert o["coverage_map"].shape == (50, 50)

    def test_agents_list_populated(self):
        env = MultiAgentEnv(num_agents=2)
        env.reset(seed=0)
        assert env.agents == ["robot_0", "robot_1"]


class TestMultiAgentEnvStep:
    def test_step_returns_correct_structure(self):
        env = MultiAgentEnv(num_agents=2)
        env.reset(seed=42)
        actions = {agent: np.zeros(3, dtype=np.float32) for agent in env.agents}
        obs, rewards, terms, truncs, infos = env.step(actions)
        assert "robot_0" in obs
        assert "robot_0" in rewards
        assert "robot_0" in terms
        assert "robot_0" in truncs
        assert isinstance(rewards["robot_0"], float)

    def test_coverage_increases(self):
        env = MultiAgentEnv(num_agents=2)
        env.reset(seed=42)
        initial_coverage = float(env._coverage_map.mean())

        actions = {agent: np.array([1.0, 0.0, 0.5], dtype=np.float32) for agent in env.agents}
        for _ in range(20):
            if not env.agents:
                break
            env.step(actions)

        final_coverage = float(env._coverage_map.mean())
        assert final_coverage > initial_coverage

    def test_truncation_at_max_steps(self):
        env = MultiAgentEnv(num_agents=2, max_steps=5)
        env.reset(seed=42)
        actions = {agent: np.zeros(3, dtype=np.float32) for agent in env.agents}
        for _ in range(4):
            _, _, _, truncs, _ = env.step(actions)
            assert not truncs["robot_0"]

        _, _, _, truncs, _ = env.step(actions)
        assert truncs["robot_0"] is True
        assert env.agents == []

    def test_collision_penalty(self):
        env = MultiAgentEnv(num_agents=2, collision_radius=100.0)
        env.reset(seed=42)
        actions = {agent: np.zeros(3, dtype=np.float32) for agent in env.agents}
        _, rewards, _, _, _ = env.step(actions)
        for agent in rewards:
            assert rewards[agent] < 0

    def test_action_clipping(self):
        env = MultiAgentEnv(num_agents=2, arena_size=10.0)
        env.reset(seed=42)
        actions = {agent: np.array([100.0, 100.0, 100.0], dtype=np.float32) for agent in env.agents}
        env.step(actions)
        for agent in env.possible_agents:
            pose = env._poses[agent]
            assert abs(pose[0]) <= 10.0
            assert abs(pose[1]) <= 10.0


class TestMultiAgentEnvSpaces:
    def test_observation_space(self):
        env = MultiAgentEnv(num_agents=2)
        space = env.observation_space("robot_0")
        assert "image" in space.spaces
        assert "lidar" in space.spaces
        assert "pose" in space.spaces
        assert "other_poses" in space.spaces
        assert "coverage_map" in space.spaces

    def test_action_space(self):
        env = MultiAgentEnv(num_agents=2)
        space = env.action_space("robot_0")
        assert space.shape == (3,)
        assert space.low[0] == -1.0
        assert space.high[0] == 1.0


class TestMultiAgentRegistration:
    def test_importable_from_gym_package(self):
        from threewe.gym import MultiAgentEnv as ImportedEnv

        env = ImportedEnv(num_agents=2)
        obs, _ = env.reset(seed=0)
        assert len(obs) == 2
