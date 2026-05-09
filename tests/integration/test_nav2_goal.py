# SPDX-License-Identifier: Apache-2.0
"""Integration tests for Nav2 goal navigation.

Validates that:
- A NavigateToPose goal is accepted by the Nav2 action server
- The robot produces odometry while navigating
- The goal eventually succeeds (simulation) or is at least acknowledged
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from geometry_msgs.msg import PoseStamped  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402

try:
    from nav2_msgs.action import NavigateToPose
except ImportError:
    pytest.skip(
        "nav2_msgs not available — skipping navigation tests", allow_module_level=True
    )

from rclpy.action import ActionClient  # noqa: E402

from conftest import topic_collector  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalPose:
    """Immutable representation of a 2D navigation goal."""

    x: float
    y: float
    yaw: float = 0.0


def _make_pose_stamped(goal: GoalPose, frame_id: str = "map") -> PoseStamped:
    """Build a PoseStamped message from a GoalPose."""
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.header.stamp.sec = 0
    pose.header.stamp.nanosec = 0
    pose.pose.position.x = goal.x
    pose.pose.position.y = goal.y
    pose.pose.position.z = 0.0
    # Simple yaw-only quaternion
    pose.pose.orientation.z = math.sin(goal.yaw / 2.0)
    pose.pose.orientation.w = math.cos(goal.yaw / 2.0)
    return pose


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.simulation
@pytest.mark.timeout(60)
class TestNav2Goal:
    """Navigation goal acceptance and execution verification."""

    def test_navigate_to_pose_goal_accepted(self, test_node: Any) -> None:
        """Sending a NavigateToPose goal should be accepted by Nav2."""
        action_client = ActionClient(
            test_node,
            NavigateToPose,
            "navigate_to_pose",
        )

        assert action_client.wait_for_server(timeout_sec=15.0), (
            "NavigateToPose action server not available"
        )

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = _make_pose_stamped(GoalPose(x=1.0, y=0.0, yaw=0.0))

        future = action_client.send_goal_async(goal_msg)

        # Spin until goal response received
        deadline = time.monotonic() + 15.0
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.1)

        assert future.done(), "Goal send did not complete within timeout"

        goal_handle = future.result()
        assert goal_handle is not None
        assert goal_handle.accepted, "Navigation goal was rejected by Nav2"

        # Cancel the goal to clean up
        cancel_future = goal_handle.cancel_goal_async()
        deadline = time.monotonic() + 5.0
        while not cancel_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.1)

        action_client.destroy()

    def test_odometry_published_during_navigation(self, test_node: Any) -> None:
        """Odometry should be published while the robot is navigating."""
        action_client = ActionClient(
            test_node,
            NavigateToPose,
            "navigate_to_pose",
        )

        if not action_client.wait_for_server(timeout_sec=15.0):
            action_client.destroy()
            pytest.skip("NavigateToPose action server not available")

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = _make_pose_stamped(GoalPose(x=2.0, y=0.0, yaw=0.0))

        future = action_client.send_goal_async(goal_msg)
        deadline = time.monotonic() + 10.0
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.1)

        if not future.done() or not future.result().accepted:
            action_client.destroy()
            pytest.skip("Goal not accepted — cannot verify odometry during nav")

        goal_handle = future.result()

        # Collect odometry messages during navigation
        odom_messages = topic_collector(
            test_node,
            "/odom",
            Odometry,
            timeout=10.0,
            count=5,
        )

        assert len(odom_messages) > 0, "No odometry messages received during navigation"

        # Verify odometry has valid frame
        for msg in odom_messages:
            assert msg.header.frame_id != ""
            assert msg.child_frame_id != ""

        # Clean up
        cancel_future = goal_handle.cancel_goal_async()
        deadline = time.monotonic() + 5.0
        while not cancel_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.1)

        action_client.destroy()

    def test_navigation_goal_reaches_destination(self, test_node: Any) -> None:
        """In simulation, robot should reach a nearby goal within timeout."""
        action_client = ActionClient(
            test_node,
            NavigateToPose,
            "navigate_to_pose",
        )

        if not action_client.wait_for_server(timeout_sec=15.0):
            action_client.destroy()
            pytest.skip("NavigateToPose action server not available")

        # Short goal: 0.5m forward
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = _make_pose_stamped(GoalPose(x=0.5, y=0.0, yaw=0.0))

        future = action_client.send_goal_async(goal_msg)
        deadline = time.monotonic() + 10.0
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.1)

        if not future.done() or not future.result().accepted:
            action_client.destroy()
            pytest.skip("Goal not accepted")

        goal_handle = future.result()

        # Wait for result
        result_future = goal_handle.get_result_async()
        deadline = time.monotonic() + 30.0
        while not result_future.done() and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=0.2)

        action_client.destroy()

        if not result_future.done():
            pytest.fail("Navigation did not complete within 30s timeout")

        result = result_future.result()
        # Status 4 = SUCCEEDED in action_msgs
        assert result.status == 4, f"Navigation did not succeed, status={result.status}"
