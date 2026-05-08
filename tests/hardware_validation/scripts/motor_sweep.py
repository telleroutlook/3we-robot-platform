#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Motor sweep test — command each wheel individually to verify direction and PWM."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time
import sys


class MotorSweep(Node):
    def __init__(self):
        super().__init__("motor_sweep")
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.get_logger().info("Motor sweep test ready")

    def send_cmd(self, vx: float, vy: float, wz: float, duration: float):
        msg = Twist()
        msg.linear.x = vx
        msg.linear.y = vy
        msg.angular.z = wz
        end_time = time.time() + duration
        while time.time() < end_time:
            self.pub.publish(msg)
            time.sleep(0.02)
        self.stop()

    def stop(self):
        msg = Twist()
        self.pub.publish(msg)

    def test_individual_wheels(self):
        speed = 0.15
        duration = 2.0
        k = 0.19  # LX + LY = 0.09 + 0.10

        tests = [
            ("FL only (vx-vy-wz*k)", speed, -speed, -speed / k),
            ("FR only (vx+vy+wz*k)", speed, speed, speed / k),
            ("RL only (vx+vy-wz*k)", speed, speed, -speed / k),
            ("RR only (vx-vy+wz*k)", speed, -speed, speed / k),
        ]

        for name, vx, vy, wz in tests:
            self.get_logger().info(f"Testing {name} for {duration}s...")
            self.send_cmd(vx, vy, wz, duration)
            time.sleep(1.0)

    def test_motions(self):
        speed = 0.15
        duration = 2.0

        motions = [
            ("Forward", speed, 0.0, 0.0),
            ("Backward", -speed, 0.0, 0.0),
            ("Strafe Left", 0.0, speed, 0.0),
            ("Strafe Right", 0.0, -speed, 0.0),
            ("Rotate CCW", 0.0, 0.0, 0.5),
            ("Rotate CW", 0.0, 0.0, -0.5),
        ]

        for name, vx, vy, wz in motions:
            self.get_logger().info(f"Motion: {name} for {duration}s...")
            self.send_cmd(vx, vy, wz, duration)
            time.sleep(1.0)


def main():
    rclpy.init()
    node = MotorSweep()

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    try:
        if mode == "individual":
            node.test_individual_wheels()
        elif mode == "motions":
            node.test_motions()
        else:
            node.get_logger().info("=== Individual wheel test ===")
            node.test_individual_wheels()
            time.sleep(2.0)
            node.get_logger().info("=== Motion test ===")
            node.test_motions()
    except KeyboardInterrupt:
        node.stop()
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
