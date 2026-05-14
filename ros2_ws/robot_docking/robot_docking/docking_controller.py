# SPDX-License-Identifier: Apache-2.0
"""
Docking controller — orchestrates the three-stage autonomous docking sequence:
1. APPROACH: Nav2 navigates to a waypoint near the charging station
2. VISUAL_SERVO_COARSE: AprilTag large marker guides coarse alignment
3. VISUAL_SERVO_FINE: AprilTag small marker guides final approach
4. CONTACT_VERIFY: Check charging voltage confirms physical contact
"""

import math
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, GoalResponse, CancelResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup

from geometry_msgs.msg import Twist, PoseStamped, Quaternion
from std_msgs.msg import Bool

from robot_docking.constants import DockingStage  # noqa: F401


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.w = math.cos(yaw / 2.0)
    q.z = math.sin(yaw / 2.0)
    return q


class DockingController(Node):
    def __init__(self) -> None:
        super().__init__("docking_controller")

        self.declare_parameter("approach_waypoint_x", 0.0)
        self.declare_parameter("approach_waypoint_y", 0.0)
        self.declare_parameter("approach_waypoint_yaw", 0.0)
        self.declare_parameter("coarse_tag_id", 0)
        self.declare_parameter("fine_tag_id", 1)
        self.declare_parameter("approach_timeout_s", 60.0)
        self.declare_parameter("servo_timeout_s", 30.0)
        self.declare_parameter("max_retries", 2)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("contact_confirmed_topic", "/docking/contact_confirmed")

        self._stage = DockingStage.IDLE
        self._retries = 0
        self._contact_confirmed = False
        self._stage_start_time: Optional[float] = None
        self._nav2_goal_handle = None
        self._nav2_result_future = None

        cmd_vel_topic = (
            self.get_parameter("cmd_vel_topic").get_parameter_value().string_value
        )
        contact_topic = (
            self.get_parameter("contact_confirmed_topic")
            .get_parameter_value()
            .string_value
        )

        self._cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self._servo_enable_pub = self.create_publisher(
            Bool, "/docking/servo_enabled", 10
        )

        self._contact_sub = self.create_subscription(
            Bool, contact_topic, self._on_contact, 10
        )

        self._tag_pose: Optional[PoseStamped] = None
        self._tag_pose_sub = self.create_subscription(
            PoseStamped, "/docking/tag_pose", self._on_tag_pose, 10
        )

        cb_group = ReentrantCallbackGroup()

        nav_action_type = self._get_navigate_action_type()
        if nav_action_type is None:
            self._nav2_client = None
        else:
            self._nav2_client = ActionClient(self, nav_action_type, "navigate_to_pose")

        dock_action_type = self._get_dock_action_type()
        if dock_action_type is None:
            self._action_server = None
        else:
            self._action_server = ActionServer(
                self,
                dock_action_type,
                "dock",
                execute_callback=self._execute_dock,
                goal_callback=self._goal_callback,
                cancel_callback=self._cancel_callback,
                callback_group=cb_group,
            )

        self._timer = self.create_timer(0.1, self._control_loop)
        self._goal_handle: Optional[ServerGoalHandle] = None

        self.get_logger().info("Docking controller initialized")

    def _get_navigate_action_type(self):
        try:
            from nav2_msgs.action import NavigateToPose

            return NavigateToPose
        except ImportError:
            self.get_logger().warn(
                "nav2_msgs not available — navigation action disabled"
            )
            return None

    def _get_dock_action_type(self):
        try:
            from robot_interfaces.action import Dock

            return Dock
        except ImportError:
            self.get_logger().warn(
                "robot_interfaces not available — action server disabled"
            )
            return None

    def _goal_callback(self, goal_request) -> GoalResponse:
        if self._stage not in (DockingStage.IDLE, DockingStage.DOCKED):
            self.get_logger().warn("Rejecting dock goal — already docking")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle: ServerGoalHandle) -> CancelResponse:
        self.get_logger().info("Dock action cancel requested")
        return CancelResponse.ACCEPT

    def _on_contact(self, msg: Bool) -> None:
        self._contact_confirmed = msg.data

    def _on_tag_pose(self, msg: PoseStamped) -> None:
        self._tag_pose = msg

    def _execute_dock(self, goal_handle: ServerGoalHandle):
        self.get_logger().info("Executing dock action")
        self._goal_handle = goal_handle
        self._stage = DockingStage.APPROACH
        self._stage_start_time = self.get_clock().now().nanoseconds / 1e9
        self._retries = 0
        self._contact_confirmed = False

        self._send_nav2_goal()

        start_time = self.get_clock().now().nanoseconds / 1e9

        rate = self.create_rate(10)
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self._cancel_nav2_goal()
                self._set_servo_enabled(False)
                self._stop_robot()
                self._stage = DockingStage.IDLE
                goal_handle.canceled()
                return self._make_result(False, "Cancelled by user", start_time)

            if self._stage == DockingStage.DOCKED:
                goal_handle.succeed()
                return self._make_result(True, "", start_time)

            if self._stage == DockingStage.FAILED:
                goal_handle.abort()
                return self._make_result(False, "Docking failed", start_time)

            self._publish_feedback(goal_handle)
            rate.sleep()

        goal_handle.abort()
        return self._make_result(False, "Node shutdown", start_time)

    def _send_nav2_goal(self) -> None:
        from nav2_msgs.action import NavigateToPose

        wp_x = self.get_parameter("approach_waypoint_x").value
        wp_y = self.get_parameter("approach_waypoint_y").value
        wp_yaw = self.get_parameter("approach_waypoint_yaw").value

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = wp_x
        goal_msg.pose.pose.position.y = wp_y
        goal_msg.pose.pose.orientation = _yaw_to_quaternion(wp_yaw)

        self.get_logger().info(
            f"Sending Nav2 goal: ({wp_x:.2f}, {wp_y:.2f}, yaw={wp_yaw:.2f})"
        )

        if self._nav2_client is None:
            self.get_logger().error("Nav2 client unavailable (nav2_msgs not installed)")
            self._stage = DockingStage.FAILED
            return

        if not self._nav2_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Nav2 action server not available")
            self._stage = DockingStage.FAILED
            return

        send_goal_future = self._nav2_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self._nav2_goal_response_callback)

    def _nav2_goal_response_callback(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Nav2 goal rejected")
            self._stage = DockingStage.FAILED
            return

        self._nav2_goal_handle = goal_handle
        self._nav2_result_future = goal_handle.get_result_async()
        self._nav2_result_future.add_done_callback(self._nav2_result_callback)

    def _nav2_result_callback(self, future) -> None:
        result = future.result()
        if result.status == 4:
            self.get_logger().info("Nav2 approach complete — switching to visual servo")
            self._stage = DockingStage.VISUAL_SERVO_COARSE
            self._stage_start_time = self.get_clock().now().nanoseconds / 1e9
            self._set_servo_enabled(True)
        else:
            self.get_logger().error(f"Nav2 approach failed (status={result.status})")
            max_retries = self.get_parameter("max_retries").value
            self._retries += 1
            if self._retries <= max_retries:
                self.get_logger().info(
                    f"Retrying approach ({self._retries}/{max_retries})"
                )
                self._send_nav2_goal()
            else:
                self._stage = DockingStage.FAILED

    def _cancel_nav2_goal(self) -> None:
        if self._nav2_goal_handle is not None:
            self._nav2_goal_handle.cancel_goal_async()
            self._nav2_goal_handle = None

    def _set_servo_enabled(self, enabled: bool) -> None:
        msg = Bool()
        msg.data = enabled
        self._servo_enable_pub.publish(msg)

    def _make_result(self, success: bool, error: str, start_time: float):
        try:
            from robot_interfaces.action import Dock

            result = Dock.Result()
            result.success = success
            result.error_message = error
            result.total_duration_sec = float(
                self.get_clock().now().nanoseconds / 1e9 - start_time
            )
            return result
        except ImportError:
            return None

    def _publish_feedback(self, goal_handle: ServerGoalHandle) -> None:
        try:
            from robot_interfaces.action import Dock

            feedback = Dock.Feedback()
            feedback.stage = int(self._stage)
            feedback.progress = self._estimate_progress()
            feedback.distance_to_dock = self._get_distance_to_dock()
            goal_handle.publish_feedback(feedback)
        except ImportError:
            pass

    def _get_distance_to_dock(self) -> float:
        if self._tag_pose is None:
            return -1.0
        p = self._tag_pose.pose.position
        return math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)

    def _estimate_progress(self) -> float:
        stage_progress = {
            DockingStage.IDLE: 0.0,
            DockingStage.APPROACH: 0.2,
            DockingStage.VISUAL_SERVO_COARSE: 0.5,
            DockingStage.VISUAL_SERVO_FINE: 0.8,
            DockingStage.CONTACT_VERIFY: 0.95,
            DockingStage.DOCKED: 1.0,
        }
        return stage_progress.get(self._stage, 0.0)

    def _control_loop(self) -> None:
        if self._stage == DockingStage.IDLE or self._stage == DockingStage.DOCKED:
            return

        if self._stage == DockingStage.FAILED:
            return

        now = self.get_clock().now().nanoseconds / 1e9

        if self._stage == DockingStage.APPROACH:
            timeout = (
                self.get_parameter("approach_timeout_s")
                .get_parameter_value()
                .double_value
            )
            if self._stage_start_time and now - self._stage_start_time > timeout:
                self.get_logger().error("Approach timed out")
                self._cancel_nav2_goal()
                self._stop_robot()
                self._stage = DockingStage.FAILED
                return

        if self._stage in (
            DockingStage.VISUAL_SERVO_COARSE,
            DockingStage.VISUAL_SERVO_FINE,
        ):
            timeout = (
                self.get_parameter("servo_timeout_s").get_parameter_value().double_value
            )
            if self._stage_start_time and now - self._stage_start_time > timeout:
                self.get_logger().error("Visual servo timed out")
                self._set_servo_enabled(False)
                self._stop_robot()
                self._stage = DockingStage.FAILED
                return

            dist = self._get_distance_to_dock()
            if self._stage == DockingStage.VISUAL_SERVO_COARSE and 0 < dist < 0.3:
                self.get_logger().info(
                    "Coarse alignment done — switching to fine servo"
                )
                self._stage = DockingStage.VISUAL_SERVO_FINE
                self._stage_start_time = now

            if self._stage == DockingStage.VISUAL_SERVO_FINE and 0 < dist < 0.06:
                self.get_logger().info("Fine approach done — verifying contact")
                self._set_servo_enabled(False)
                self._stop_robot()
                self._stage = DockingStage.CONTACT_VERIFY
                self._stage_start_time = now

        if self._stage == DockingStage.CONTACT_VERIFY:
            if self._contact_confirmed:
                self.get_logger().info("Contact confirmed — docked!")
                self._stage = DockingStage.DOCKED
            elif self._stage_start_time and now - self._stage_start_time > 5.0:
                self.get_logger().error("Contact verification timed out")
                self._stage = DockingStage.FAILED

    def _stop_robot(self) -> None:
        self._cmd_pub.publish(Twist())

    @property
    def stage(self) -> DockingStage:
        return self._stage


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = DockingController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
