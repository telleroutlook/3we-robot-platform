# SPDX-License-Identifier: Apache-2.0
"""Tests for Isaac Sim training loop."""

from __future__ import annotations

import numpy as np
import pytest

from threewe.backends.isaac_training import IsaacSimTrainingLoop, TrainingConfig


class TestTrainingConfig:
    def test_default_values(self):
        config = TrainingConfig()
        assert config.num_envs == 64
        assert config.headless is True
        assert config.max_episode_steps == 500
        assert config.scene == "office_v2"

    def test_custom_values(self):
        config = TrainingConfig(num_envs=16, headless=False, max_episode_steps=200)
        assert config.num_envs == 16
        assert config.headless is False
        assert config.max_episode_steps == 200

    def test_frozen(self):
        config = TrainingConfig()
        with pytest.raises(AttributeError):
            config.num_envs = 32  # type: ignore[misc]

    def test_observation_keys(self):
        config = TrainingConfig()
        assert "image" in config.observation_keys
        assert "lidar" in config.observation_keys
        assert "pose" in config.observation_keys
        assert "velocity" in config.observation_keys


class TestIsaacSimTrainingLoop:
    def test_reset_returns_batched_obs(self):
        config = TrainingConfig(num_envs=8)
        loop = IsaacSimTrainingLoop(config)
        obs = loop.reset(seed=42)
        assert "image" in obs
        assert obs["image"].shape == (8, 64, 64, 3)
        assert obs["lidar"].shape == (8, 360)
        assert obs["pose"].shape == (8, 3)
        assert obs["velocity"].shape == (8, 3)

    def test_step_returns_correct_shapes(self):
        config = TrainingConfig(num_envs=4)
        loop = IsaacSimTrainingLoop(config)
        loop.reset()
        actions = np.zeros((4, 3), dtype=np.float32)
        obs, rewards, dones, truncs, infos = loop.step(actions)
        assert rewards.shape == (4,)
        assert dones.shape == (4,)
        assert truncs.shape == (4,)
        assert len(infos) == 4

    def test_step_count_increments(self):
        config = TrainingConfig(num_envs=2)
        loop = IsaacSimTrainingLoop(config)
        loop.reset()
        assert loop.step_count == 0
        loop.step(np.zeros((2, 3), dtype=np.float32))
        assert loop.step_count == 1
        loop.step(np.zeros((2, 3), dtype=np.float32))
        assert loop.step_count == 2

    def test_truncation_at_max_steps(self):
        config = TrainingConfig(num_envs=2, max_episode_steps=3)
        loop = IsaacSimTrainingLoop(config)
        loop.reset()
        actions = np.zeros((2, 3), dtype=np.float32)
        for _ in range(2):
            _, _, _, truncs, _ = loop.step(actions)
            assert not truncs.any()
        _, _, _, truncs, _ = loop.step(actions)
        assert truncs.all()

    def test_auto_reset_on_truncation(self):
        config = TrainingConfig(num_envs=2, max_episode_steps=2)
        loop = IsaacSimTrainingLoop(config)
        loop.reset()
        actions = np.zeros((2, 3), dtype=np.float32)
        loop.step(actions)
        loop.step(actions)
        # After truncation, episode steps reset
        _, _, _, truncs, _ = loop.step(actions)
        # Next step after auto-reset should not be truncated
        assert not truncs.any()

    def test_close(self):
        config = TrainingConfig(num_envs=2)
        loop = IsaacSimTrainingLoop(config)
        loop.reset()
        loop.close()
        assert not loop._initialized

    def test_num_envs_property(self):
        config = TrainingConfig(num_envs=16)
        loop = IsaacSimTrainingLoop(config)
        assert loop.num_envs == 16

    def test_seed(self):
        config = TrainingConfig(num_envs=2)
        loop = IsaacSimTrainingLoop(config)
        loop.seed(123)
        obs1 = loop.reset()
        loop.seed(123)
        obs2 = loop.reset()
        np.testing.assert_array_equal(obs1["pose"], obs2["pose"])
