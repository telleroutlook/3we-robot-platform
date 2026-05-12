# SPDX-License-Identifier: Apache-2.0
"""Collection manager node — Action Server orchestrating the full ball
collection cycle: SEARCHING → APPROACHING → PICKING → RETURNING → DUMPING.

Modeled on the docking_controller.py pattern: a 10 Hz control loop drives
state transitions while the action server handles goal lifecycle.
"""

from __future__ import annotations

import math
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup

from geometry_msgs.msg import PoseStamped, Quaternion, Twist
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from robot_collection.constants import CollectionStage


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.w = math.cos(yaw / 2.0)
    q.z = math.sin(yaw / 2.0)
    return q


class CollectionManagerNode(Node):
    """Orchestrate ball collection via Nav2, arm, and basket services."""

    def __init__(self) -> None:
        super().__init__("collection_manager")

        self.declare_parameter("search_timeout_s", 30.0)
        self.declare_parameter("approach_distance_m", 0.15)
        self.declare_parameter("basket_capacity", 6)
        self.declare_parameter("max_pick_retries", 2)
        self.declare_parameter("low_battery_threshold", 20.0)
        self.declare_parameter("dump_zone_x", 0.0)
        self.declare_parameter("dump_zone_y", 0.0)
        self.declare_parameter("dump_zone_yaw", 1.5708)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")

        self._stage = CollectionStage.IDLE
        self._balls_in_basket = 0
        self._total_collected = 0
        self._pick_retries = 0
        self._stage_start_time: Optional[float] = None
        self._battery_percent = 100.0
        self._ball_target: Optional[PoseStamped] = None
        self._arm_status = "idle"
        self._nav2_goal_handle = None
        self._nav2_result_future = None
        self._nav2_succeeded = False
        self._nav2_done = False

        cmd_vel_topic = self.get_parameter("cmd_vel_topic").value

        self._cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self._state_pub = None
        self._create_state_publisher()

        self._ball_target_sub = self.create_subscription(
            PoseStamped, "/collection/ball_target", self._on_ball_target, 10
        )
        self._arm_status_sub = self.create_subscription(
            String, "/collection/arm_status", self._on_arm_status, 10
        )
        self._battery_sub = self.create_subscription(
            BatteryState, "/battery_state", self._on_battery, 10
        )

        cb_group = ReentrantCallbackGroup()

        self._nav2_client = self._create_nav2_client()
        self._arm_client = None
        self._basket_client = None
        self._create_service_clients()

        self._action_server = self._create_action_server(cb_group)

        self._timer = self.create_timer(0.1, self._control_loop)
        self._goal_handle: Optional[ServerGoalHandle] = None

        self.get_logger().info("Collection manager started")

    def _create_state_publisher(self) -> None:
        try:
            from robot_interfaces.msg import CollectionState

            self._state_pub = self.create_publisher(
                CollectionState, "/collection/state", 10
            )
        except ImportError:
            self.get_logger().warn(
                "robot_interfaces not available — state pub disabled"
            )

    def _create_nav2_client(self) -> Optional[ActionClient]:
        try:
            from nav2_msgs.action import NavigateToPose

            return ActionClient(self, NavigateToPose, "navigate_to_pose")
        except ImportError:
            self.get_logger().warn("nav2_msgs not available — navigation disabled")
            return None

    def _create_service_clients(self) -> None:
        try:
            from robot_interfaces.srv import ArmCommand, BasketDump

            self._arm_client = self.create_client(ArmCommand, "/collection/arm_command")
            self._basket_client = self.create_client(
                BasketDump, "/collection/basket_dump"
            )
        except ImportError:
            self.get_logger().warn(
                "robot_interfaces not available — service clients disabled"
            )

    def _create_action_server(self, cb_group) -> Optional[ActionServer]:
        try:
            from robot_interfaces.action import CollectBalls

            return ActionServer(
                self,
                CollectBalls,
                "collect_balls",
                execute_callback=self._execute_collection,
                goal_callback=self._goal_callback,
                cancel_callback=self._cancel_callback,
                callback_group=cb_group,
            )
        except ImportError:
            self.get_logger().warn(
                "robot_interfaces not available — action server disabled"
            )
            return None

    def _goal_callback(self, goal_request) -> GoalResponse:
        if self._stage != CollectionStage.IDLE:
            self.get_logger().warn("Rejecting goal — collection already active")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle: ServerGoalHandle) -> CancelResponse:
        self.get_logger().info("Collection cancel requested")
        return CancelResponse.ACCEPT

    def _on_ball_target(self, msg: PoseStamped) -> None:
        self._ball_target = msg

    def _on_arm_status(self, msg: String) -> None:
        self._arm_status = msg.data

    def _on_battery(self, msg: BatteryState) -> None:
        self._battery_percent = msg.percentage * 100.0

    def _execute_collection(self, goal_handle: ServerGoalHandle):
        self.get_logger().info("Executing collection action")
        self._goal_handle = goal_handle
        self._stage = CollectionStage.SEARCHING
        self._stage_start_time = self._now()
        self._balls_in_basket = 0
        self._total_collected = 0
        self._pick_retries = 0
        self._ball_target = None

        max_balls = goal_handle.request.max_balls
        start_time = self._now()

        rate = self.create_rate(10)
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self._cancel_navigation()
                self._stop_robot()
                self._stage = CollectionStage.IDLE
                self._publish_state()
                goal_handle.canceled()
                return self._make_result(False, "Cancelled by user", start_time)

            low_battery = self.get_parameter("low_battery_threshold").value
            if self._battery_percent < low_battery:
                self._cancel_navigation()
                self._stop_robot()
                self._stage = CollectionStage.IDLE
                self._publish_state()
                goal_handle.abort()
                return self._make_result(False, "Low battery", start_time)

            if self._stage == CollectionStage.IDLE:
                goal_handle.succeed()
                return self._make_result(True, "", start_time)

            if max_balls > 0 and self._total_collected >= max_balls:
                self._stage = CollectionStage.IDLE
                self._publish_state()
                goal_handle.succeed()
                return self._make_result(True, "", start_time)

            self._publish_feedback(goal_handle)
            rate.sleep()

        goal_handle.abort()
        return self._make_result(False, "Node shutdown", start_time)

    def _control_loop(self) -> None:
        if self._stage == CollectionStage.IDLE:
            return

        self._publish_state()
        now = self._now()

        if self._stage == CollectionStage.SEARCHING:
            self._handle_searching(now)
        elif self._stage == CollectionStage.APPROACHING:
            self._handle_approaching()
        elif self._stage == CollectionStage.PICKING:
            self._handle_picking()
        elif self._stage == CollectionStage.RETURNING:
            self._handle_returning()
        elif self._stage == CollectionStage.DUMPING:
            self._handle_dumping()

    def _handle_searching(self, now: float) -> None:
        timeout = self.get_parameter("search_timeout_s").value
        if self._stage_start_time and now - self._stage_start_time > timeout:
            self.get_logger().info("Search timed out — stopping")
            self._stop_robot()
            self._stage = CollectionStage.IDLE
            return

        if self._ball_target is not None:
            self.get_logger().info("Ball detected — approaching")
            self._stage = CollectionStage.APPROACHING
            self._stage_start_time = now
            self._send_nav2_to_ball()

        # Slow rotation while searching
        twist = Twist()
        twist.angular.z = 0.3
        self._cmd_pub.publish(twist)

    def _handle_approaching(self) -> None:
        if self._ball_target is None:
            self.get_logger().info("Lost ball target — back to searching")
            self._cancel_navigation()
            self._stage = CollectionStage.SEARCHING
            self._stage_start_time = self._now()
            return

        if self._nav2_done:
            self._nav2_done = False
            if self._nav2_succeeded:
                self.get_logger().info("Arrived at ball — picking")
                self._stage = CollectionStage.PICKING
                self._stage_start_time = self._now()
                self._pick_retries = 0
                self._request_arm_pick()
            else:
                self.get_logger().warn("Nav2 failed — back to searching")
                self._stage = CollectionStage.SEARCHING
                self._stage_start_time = self._now()

    def _handle_picking(self) -> None:
        if self._arm_status == "idle":
            self._balls_in_basket += 1
            self._total_collected += 1
            self.get_logger().info(
                f"Pick success — basket: {self._balls_in_basket}, "
                f"total: {self._total_collected}"
            )
            self._ball_target = None

            basket_capacity = self.get_parameter("basket_capacity").value
            if self._balls_in_basket >= basket_capacity:
                self.get_logger().info("Basket full — returning to dump")
                self._stage = CollectionStage.RETURNING
                self._stage_start_time = self._now()
                self._send_nav2_to_dump_zone()
            else:
                self._stage = CollectionStage.SEARCHING
                self._stage_start_time = self._now()

        elif self._arm_status == "error":
            max_retries = self.get_parameter("max_pick_retries").value
            self._pick_retries += 1
            if self._pick_retries <= max_retries:
                self.get_logger().warn(
                    f"Pick failed — retry {self._pick_retries}/{max_retries}"
                )
                self._request_arm_pick()
            else:
                self.get_logger().warn("Pick failed — skipping ball")
                self._ball_target = None
                self._stage = CollectionStage.SEARCHING
                self._stage_start_time = self._now()

    def _handle_returning(self) -> None:
        if self._nav2_done:
            self._nav2_done = False
            if self._nav2_succeeded:
                self.get_logger().info("Arrived at dump zone — dumping")
                self._stage = CollectionStage.DUMPING
                self._stage_start_time = self._now()
                self._request_basket_dump()
            else:
                self.get_logger().warn("Return nav failed — retrying")
                self._send_nav2_to_dump_zone()

    def _handle_dumping(self) -> None:
        # Wait for basket controller to finish (check basket_state topic)
        # For simplicity, transition after dump_hold_time
        dump_time = 3.0  # dump_hold + reset
        if self._stage_start_time and self._now() - self._stage_start_time > dump_time:
            self._balls_in_basket = 0
            self.get_logger().info("Dump complete — resuming search")
            self._stage = CollectionStage.SEARCHING
            self._stage_start_time = self._now()

    def _send_nav2_to_ball(self) -> None:
        if self._nav2_client is None or self._ball_target is None:
            return

        try:
            from nav2_msgs.action import NavigateToPose
        except ImportError:
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._ball_target
        goal_msg.pose.header.frame_id = "map"

        self._nav2_done = False
        self._nav2_succeeded = False

        if not self._nav2_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("Nav2 not available")
            self._nav2_done = True
            self._nav2_succeeded = False
            return

        future = self._nav2_client.send_goal_async(goal_msg)
        future.add_done_callback(self._nav2_goal_response)

    def _send_nav2_to_dump_zone(self) -> None:
        if self._nav2_client is None:
            return

        try:
            from nav2_msgs.action import NavigateToPose
        except ImportError:
            return

        dump_x = self.get_parameter("dump_zone_x").value
        dump_y = self.get_parameter("dump_zone_y").value
        dump_yaw = self.get_parameter("dump_zone_yaw").value

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = dump_x
        goal_msg.pose.pose.position.y = dump_y
        goal_msg.pose.pose.orientation = _yaw_to_quaternion(dump_yaw)

        self._nav2_done = False
        self._nav2_succeeded = False

        if not self._nav2_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("Nav2 not available")
            self._nav2_done = True
            return

        future = self._nav2_client.send_goal_async(goal_msg)
        future.add_done_callback(self._nav2_goal_response)

    def _nav2_goal_response(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Nav2 goal rejected")
            self._nav2_done = True
            self._nav2_succeeded = False
            return

        self._nav2_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._nav2_result_callback)

    def _nav2_result_callback(self, future) -> None:
        result = future.result()
        self._nav2_done = True
        self._nav2_succeeded = result.status == 4  # STATUS_SUCCEEDED

    def _cancel_navigation(self) -> None:
        if self._nav2_goal_handle is not None:
            self._nav2_goal_handle.cancel_goal_async()
            self._nav2_goal_handle = None

    def _request_arm_pick(self) -> None:
        if self._arm_client is None or self._ball_target is None:
            return

        try:
            from robot_interfaces.srv import ArmCommand
        except ImportError:
            return

        req = ArmCommand.Request()
        req.command = "pick"
        req.target_x = self._ball_target.pose.position.x
        req.target_y = self._ball_target.pose.position.y
        req.target_z = self._ball_target.pose.position.z

        self._arm_client.call_async(req)

    def _request_basket_dump(self) -> None:
        if self._basket_client is None:
            return

        try:
            from robot_interfaces.srv import BasketDump
        except ImportError:
            return

        req = BasketDump.Request()
        req.dump = True
        self._basket_client.call_async(req)

    def _stop_robot(self) -> None:
        self._cmd_pub.publish(Twist())

    def _publish_state(self) -> None:
        if self._state_pub is None:
            return

        try:
            from robot_interfaces.msg import CollectionState

            msg = CollectionState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.state = int(self._stage)
            msg.balls_in_basket = self._balls_in_basket
            msg.total_collected = self._total_collected
            self._state_pub.publish(msg)
        except ImportError:
            pass

    def _publish_feedback(self, goal_handle: ServerGoalHandle) -> None:
        try:
            from robot_interfaces.action import CollectBalls

            feedback = CollectBalls.Feedback()
            feedback.state = int(self._stage)
            feedback.balls_in_basket = self._balls_in_basket
            feedback.total_collected = self._total_collected
            feedback.current_phase = self._stage.name
            goal_handle.publish_feedback(feedback)
        except ImportError:
            pass

    def _make_result(self, success: bool, error: str, start_time: float):
        try:
            from robot_interfaces.action import CollectBalls

            result = CollectBalls.Result()
            result.success = success
            result.error_message = error
            result.total_collected = self._total_collected
            result.total_duration_sec = float(self._now() - start_time)
            return result
        except ImportError:
            return None

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CollectionManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
