# SPDX-License-Identifier: Apache-2.0
"""
Visual servo controller for AprilTag-guided docking approach.

Uses proportional control on lateral offset, heading error, and forward distance
to guide the robot toward the charging dock at low speed.
"""

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import Bool


@dataclass(frozen=True)
class ServoGains:
    kp_lateral: float
    kp_angular: float
    kp_forward: float
    max_linear_speed: float
    max_angular_speed: float


class VisualServoNode(Node):
    def __init__(self) -> None:
        super().__init__("visual_servo")

        self.declare_parameter("kp_lateral", 0.8)
        self.declare_parameter("kp_angular", 1.2)
        self.declare_parameter("kp_forward", 0.3)
        self.declare_parameter("max_linear_speed", 0.1)
        self.declare_parameter("max_angular_speed", 0.3)
        self.declare_parameter("target_distance_m", 0.05)
        self.declare_parameter("alignment_tolerance_m", 0.01)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("tag_pose_topic", "/docking/tag_pose")
        self.declare_parameter("enabled_topic", "/docking/servo_enabled")

        self._gains = ServoGains(
            kp_lateral=self.get_parameter("kp_lateral").value,
            kp_angular=self.get_parameter("kp_angular").value,
            kp_forward=self.get_parameter("kp_forward").value,
            max_linear_speed=self.get_parameter("max_linear_speed").value,
            max_angular_speed=self.get_parameter("max_angular_speed").value,
        )

        self._target_distance = self.get_parameter("target_distance_m").value
        self._enabled = False
        self._latest_pose: Optional[PoseStamped] = None

        cmd_vel_topic = (
            self.get_parameter("cmd_vel_topic").get_parameter_value().string_value
        )
        tag_pose_topic = (
            self.get_parameter("tag_pose_topic").get_parameter_value().string_value
        )
        enabled_topic = (
            self.get_parameter("enabled_topic").get_parameter_value().string_value
        )

        self._cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        self._pose_sub = self.create_subscription(
            PoseStamped, tag_pose_topic, self._on_tag_pose, 10
        )
        self._enable_sub = self.create_subscription(
            Bool, enabled_topic, self._on_enable, 10
        )

        self._timer = self.create_timer(0.05, self._servo_loop)
        self.get_logger().info("Visual servo node initialized")

    def _on_tag_pose(self, msg: PoseStamped) -> None:
        self._latest_pose = msg

    def _on_enable(self, msg: Bool) -> None:
        self._enabled = msg.data
        if not self._enabled:
            self._cmd_pub.publish(Twist())

    def _servo_loop(self) -> None:
        if not self._enabled or self._latest_pose is None:
            return

        pose = self._latest_pose
        lateral_error = pose.pose.position.y
        forward_distance = pose.pose.position.x
        heading_error = self._yaw_from_quaternion(pose.pose.orientation)

        cmd = Twist()

        if forward_distance > self._target_distance:
            cmd.linear.x = self._clamp(
                self._gains.kp_forward * forward_distance,
                -self._gains.max_linear_speed,
                self._gains.max_linear_speed,
            )

        cmd.linear.y = self._clamp(
            -self._gains.kp_lateral * lateral_error,
            -self._gains.max_linear_speed,
            self._gains.max_linear_speed,
        )

        cmd.angular.z = self._clamp(
            -self._gains.kp_angular * heading_error,
            -self._gains.max_angular_speed,
            self._gains.max_angular_speed,
        )

        self._cmd_pub.publish(cmd)

    @staticmethod
    def _yaw_from_quaternion(q) -> float:
        import math

        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = VisualServoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
