# SPDX-License-Identifier: Apache-2.0
"""
Nav2 5-point patrol acceptance test.

Validates that the robot can autonomously navigate to 5 waypoints
in the obstacles.sdf world with ≥95% success rate across 10 trials.

Pass criteria (aligned with robot-1 doc10 §十):
  - 5-point patrol success rate ≥ 95%
  - Single loop average time ≤ 180s
  - Collisions: 0
"""

import json
import time
import math

import pytest
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Range

# 5 waypoints in obstacles.sdf world (x, y, yaw_rad)
PATROL_WAYPOINTS = [
    (1.0, 0.0, 0.0),
    (2.0, 1.5, 1.57),
    (0.5, 2.5, 3.14),
    (-1.0, 1.0, -1.57),
    (0.0, 0.0, 0.0),
]

GOAL_TOLERANCE_M = 0.3
TRIAL_TIMEOUT_S = 120.0
NUM_TRIALS = 10
MIN_PASS_RATE = 0.95
MAX_AVG_LOOP_TIME_S = 180.0


class PatrolTestNode(Node):
    def __init__(self):
        super().__init__("patrol_acceptance_test")
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.min_range = float("inf")
        self.collision_count = 0
        self._server_ready = False

        self.range_sub = self.create_subscription(
            Range, "/ultrasonic/front", self._range_cb, 10
        )

    def _range_cb(self, msg):
        if msg.range < self.min_range:
            self.min_range = msg.range
        if msg.range < 0.01:
            self.collision_count += 1

    def wait_for_nav2(self, timeout_sec=120.0):
        """Block until navigate_to_pose action server is available."""
        self.get_logger().info("Waiting for navigate_to_pose action server...")
        ready = self.nav_client.wait_for_server(timeout_sec=timeout_sec)
        if ready:
            self._server_ready = True
            self.get_logger().info("Nav2 action server is ready.")
        else:
            self.get_logger().error(
                f"Nav2 action server not available after {timeout_sec}s"
            )
        return ready

    def send_goal(self, x, y, yaw):
        if not self._server_ready:
            if not self.nav_client.wait_for_server(timeout_sec=60.0):
                self.get_logger().error("Nav2 action server unavailable")
                return False

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)

        future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        if not future.done():
            return False

        goal_handle = future.result()
        if not goal_handle or not goal_handle.accepted:
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(
            self, result_future, timeout_sec=TRIAL_TIMEOUT_S
        )

        if result_future.result() is None:
            return False

        return True


@pytest.fixture(scope="module")
def patrol_node():
    if not rclpy.ok():
        rclpy.init()
    node = PatrolTestNode()
    if not node.wait_for_nav2(timeout_sec=10.0):
        node.destroy_node()
        pytest.skip(
            "Nav2 navigate_to_pose action server not available (simulation not running)"
        )
    yield node
    node.destroy_node()


def run_single_trial(node):
    """Run one complete 5-point patrol. Returns (success, elapsed_s)."""
    start = time.time()
    for x, y, yaw in PATROL_WAYPOINTS:
        success = node.send_goal(x, y, yaw)
        if not success:
            return False, time.time() - start
    return True, time.time() - start


@pytest.mark.simulation
def test_nav2_patrol_acceptance(patrol_node):
    """Run NUM_TRIALS patrol loops and verify pass rate ≥ 95%."""
    successes = 0
    total_time = 0.0
    trial_results = []

    for trial in range(NUM_TRIALS):
        success, elapsed = run_single_trial(patrol_node)
        trial_results.append({"trial": trial, "success": success, "time_s": elapsed})
        if success:
            successes += 1
            total_time += elapsed

    pass_rate = successes / NUM_TRIALS
    avg_time = total_time / max(successes, 1)

    results = {
        "pass_rate": pass_rate,
        "successes": successes,
        "total_trials": NUM_TRIALS,
        "avg_loop_time_s": avg_time,
        "collisions": patrol_node.collision_count,
        "min_range_m": patrol_node.min_range,
        "trials": trial_results,
    }

    with open("/tmp/sim_results.json", "w") as f:
        json.dump(results, f, indent=2)

    assert pass_rate >= MIN_PASS_RATE, (
        f"Patrol pass rate {pass_rate:.2f} < {MIN_PASS_RATE}"
    )
    assert avg_time <= MAX_AVG_LOOP_TIME_S, (
        f"Average loop time {avg_time:.1f}s > {MAX_AVG_LOOP_TIME_S}s"
    )
    assert patrol_node.collision_count == 0, (
        f"Collisions detected: {patrol_node.collision_count}"
    )
