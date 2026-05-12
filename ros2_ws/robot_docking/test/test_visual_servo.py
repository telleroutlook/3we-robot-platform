# SPDX-License-Identifier: Apache-2.0
"""Unit tests for VisualServoNode pure math functions."""

import math
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self, *a, **kw):
        pass

    def declare_parameter(self, *a, **kw):
        pass

    def get_parameter(self, name):
        defaults = {
            "kp_lateral": 0.8,
            "kp_angular": 1.2,
            "kp_forward": 0.3,
            "max_linear_speed": 0.1,
            "max_angular_speed": 0.3,
            "target_distance_m": 0.05,
            "alignment_tolerance_m": 0.01,
            "cmd_vel_topic": "/cmd_vel",
            "tag_pose_topic": "/docking/tag_pose",
            "enabled_topic": "/docking/servo_enabled",
        }
        val = defaults.get(name, 0)
        return SimpleNamespace(
            value=val,
            get_parameter_value=lambda: SimpleNamespace(
                string_value=val if isinstance(val, str) else "",
                double_value=val if isinstance(val, float) else 0.0,
                integer_value=val if isinstance(val, int) else 0,
            ),
        )

    def create_publisher(self, *a, **kw):
        return MagicMock()

    def create_subscription(self, *a, **kw):
        return MagicMock()

    def create_timer(self, *a, **kw):
        return MagicMock()

    def get_clock(self):
        return MagicMock()

    def get_logger(self):
        return MagicMock()


# Patch sys.modules before importing
_rclpy_mock = MagicMock()
_node_mod = MagicMock()
_node_mod.Node = _FakeNode
sys.modules.setdefault("rclpy", _rclpy_mock)
sys.modules["rclpy.node"] = _node_mod
sys.modules.setdefault("geometry_msgs.msg", MagicMock())
sys.modules.setdefault("std_msgs.msg", MagicMock())

from robot_docking.visual_servo import VisualServoNode  # noqa: E402


class TestYawFromQuaternion:
    def test_identity_quaternion_zero_yaw(self):
        q = SimpleNamespace(w=1.0, x=0.0, y=0.0, z=0.0)
        yaw = VisualServoNode._yaw_from_quaternion(q)
        assert yaw == pytest.approx(0.0, abs=1e-6)

    def test_90_degree_yaw(self):
        # 90 degrees around z: w=cos(45)=0.7071, z=sin(45)=0.7071
        q = SimpleNamespace(w=0.7071068, x=0.0, y=0.0, z=0.7071068)
        yaw = VisualServoNode._yaw_from_quaternion(q)
        assert yaw == pytest.approx(math.pi / 2, abs=1e-4)

    def test_180_degree_yaw(self):
        q = SimpleNamespace(w=0.0, x=0.0, y=0.0, z=1.0)
        yaw = VisualServoNode._yaw_from_quaternion(q)
        assert abs(yaw) == pytest.approx(math.pi, abs=1e-4)

    def test_negative_90_degree_yaw(self):
        q = SimpleNamespace(w=0.7071068, x=0.0, y=0.0, z=-0.7071068)
        yaw = VisualServoNode._yaw_from_quaternion(q)
        assert yaw == pytest.approx(-math.pi / 2, abs=1e-4)

    def test_small_angle(self):
        # ~10 degrees: w=cos(5°), z=sin(5°)
        angle_rad = math.radians(10)
        q = SimpleNamespace(
            w=math.cos(angle_rad / 2),
            x=0.0,
            y=0.0,
            z=math.sin(angle_rad / 2),
        )
        yaw = VisualServoNode._yaw_from_quaternion(q)
        assert yaw == pytest.approx(angle_rad, abs=1e-4)


class TestClamp:
    def test_value_within_range(self):
        assert VisualServoNode._clamp(0.5, -1.0, 1.0) == 0.5

    def test_value_above_max(self):
        assert VisualServoNode._clamp(2.0, -1.0, 1.0) == 1.0

    def test_value_below_min(self):
        assert VisualServoNode._clamp(-2.0, -1.0, 1.0) == -1.0

    def test_value_at_max(self):
        assert VisualServoNode._clamp(1.0, -1.0, 1.0) == 1.0

    def test_value_at_min(self):
        assert VisualServoNode._clamp(-1.0, -1.0, 1.0) == -1.0

    def test_zero(self):
        assert VisualServoNode._clamp(0.0, -0.3, 0.3) == 0.0

    def test_asymmetric_range(self):
        assert VisualServoNode._clamp(5.0, 0.0, 10.0) == 5.0
        assert VisualServoNode._clamp(-1.0, 0.0, 10.0) == 0.0
