# SPDX-License-Identifier: Apache-2.0
"""Tests for the Isaac Sim backend."""

from __future__ import annotations

import numpy as np
import pytest

from threewe.backends.isaac_sim import IsaacSimBackend, IsaacSimConfig


class TestIsaacSimConfig:
    def test_defaults(self):
        config = IsaacSimConfig()
        assert config.num_envs == 1
        assert config.scene == "office_v2"
        assert config.domain_randomization is False
        assert config.headless is True

    def test_custom_config(self):
        config = IsaacSimConfig(num_envs=64, scene="apartment_v1", domain_randomization=True)
        assert config.num_envs == 64
        assert config.scene == "apartment_v1"
        assert config.domain_randomization is True


class TestIsaacSimBackend:
    def test_initialization(self):
        backend = IsaacSimBackend()
        assert backend.is_connected is False
        assert backend.num_envs == 1

    def test_connect_disconnect(self):
        backend = IsaacSimBackend()
        backend.connect()
        assert backend.is_connected is True
        backend.disconnect()
        assert backend.is_connected is False

    def test_not_connected_raises(self):
        backend = IsaacSimBackend()
        with pytest.raises(RuntimeError, match="not connected"):
            backend.get_camera_image()

    def test_camera_image_shape(self):
        backend = IsaacSimBackend()
        backend.connect()
        image = backend.get_camera_image()
        assert image.shape == (480, 640, 3)
        assert image.dtype == np.uint8

    def test_lidar_shape(self):
        backend = IsaacSimBackend()
        backend.connect()
        scan = backend.get_lidar_scan()
        assert scan.ranges.shape == (360,)
        assert scan.ranges.dtype == np.float32

    def test_pose_returns_pose2d(self):
        backend = IsaacSimBackend()
        backend.connect()
        pose = backend.get_pose()
        assert hasattr(pose, "x")
        assert hasattr(pose, "y")
        assert hasattr(pose, "theta")

    @pytest.mark.asyncio
    async def test_move_to(self):
        backend = IsaacSimBackend()
        backend.connect()
        result = await backend.move_to(x=3.0, y=4.0)
        assert result.success is True
        assert result.final_pose.x == 3.0
        assert result.final_pose.y == 4.0


class TestParallelEnvironments:
    def test_parallel_observations_shape(self):
        config = IsaacSimConfig(num_envs=4)
        backend = IsaacSimBackend(config=config)
        backend.connect()
        obs = backend.get_parallel_observations()
        assert len(obs) == 4
        for o in obs:
            assert "image" in o
            assert "lidar" in o
            assert "pose" in o
            assert o["image"].shape == (480, 640, 3)
            assert o["lidar"].shape == (360,)
            assert o["pose"].shape == (3,)

    def test_step_parallel(self):
        config = IsaacSimConfig(num_envs=8)
        backend = IsaacSimBackend(config=config)
        backend.connect()
        actions = np.zeros((8, 3), dtype=np.float32)
        obs, rewards, dones, infos = backend.step_parallel(actions)
        assert len(obs) == 8
        assert rewards.shape == (8,)
        assert dones.shape == (8,)
        assert len(infos) == 8

    def test_large_num_envs(self):
        config = IsaacSimConfig(num_envs=128)
        backend = IsaacSimBackend(config=config)
        backend.connect()
        obs = backend.get_parallel_observations()
        assert len(obs) == 128

    def test_domain_randomization_no_error(self):
        config = IsaacSimConfig(num_envs=4, domain_randomization=True)
        backend = IsaacSimBackend(config=config)
        backend.connect()
        backend.apply_domain_randomization({"friction": [0.5, 1.5]})


class TestRobotIsaacIntegration:
    def test_robot_creates_isaac_backend(self):
        from threewe.robot import Robot

        robot = Robot(backend="isaac_sim", auto_connect=False)
        assert robot.backend_name == "isaac_sim"
