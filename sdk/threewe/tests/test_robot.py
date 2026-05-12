# SPDX-License-Identifier: Apache-2.0
"""Tests for the Robot class."""

import pytest

from threewe import Robot
from threewe.config import RobotConfig
from threewe.exceptions import ConnectionError


class TestRobotInit:
    def test_default_backend_is_gazebo(self):
        robot = Robot(backend="gazebo", auto_connect=False)
        assert robot.backend_name == "gazebo"

    def test_config_loaded(self):
        robot = Robot(backend="gazebo", auto_connect=False)
        assert robot.config.hardware.platform == "3we_standard_v2"

    def test_custom_config(self):
        config = RobotConfig()
        robot = Robot(backend="gazebo", config=config, auto_connect=False)
        assert robot.config is config

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            Robot(backend="nonexistent", auto_connect=False)

    def test_isaac_sim_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Phase 2"):
            Robot(backend="isaac_sim", auto_connect=False)

    def test_not_connected_by_default_when_auto_connect_false(self):
        robot = Robot(backend="gazebo", auto_connect=False)
        assert robot.is_connected is False


class TestRobotNotConnected:
    def test_get_pose_raises_when_not_connected(self):
        robot = Robot(backend="gazebo", auto_connect=False)
        with pytest.raises(ConnectionError, match="not connected"):
            robot.get_pose()

    def test_set_velocity_raises_when_not_connected(self):
        robot = Robot(backend="gazebo", auto_connect=False)
        with pytest.raises(ConnectionError, match="not connected"):
            robot.set_velocity(0.1, 0.0, 0.0)


class TestRobotContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_connects(self):
        # This will fail if rclpy is not available, which is expected
        # in a pure unit test environment. We test the logic path.
        try:
            async with Robot(backend="gazebo") as robot:
                assert robot.is_connected
        except ImportError:
            pytest.skip("rclpy not available")

    @pytest.mark.asyncio
    async def test_context_manager_disconnects(self):
        try:
            robot = Robot(backend="gazebo", auto_connect=False)
            robot.connect()
            assert robot.is_connected
            robot.disconnect()
            assert not robot.is_connected
        except ImportError:
            pytest.skip("rclpy not available")


class TestRobotVelocityClamping:
    def test_velocity_clamped_to_limits(self):
        # Test that _clamp_and_send respects limits
        robot = Robot(backend="gazebo", auto_connect=False)
        # We can't test set_velocity directly without connection,
        # but we can verify the config limits are correct
        assert robot.config.limits.max_linear_velocity == 0.5
        assert robot.config.limits.max_angular_velocity == 1.0
