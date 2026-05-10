# SPDX-License-Identifier: Apache-2.0
"""
Contact detector node — monitors charging pin ADC voltage to confirm
physical contact with the charging dock.

Subscribes to /charging/voltage (Float32) published by ESP32 firmware and
publishes /docking/contact_confirmed (Bool).
"""

from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool


class ContactDetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("contact_detector")

        self.declare_parameter("voltage_threshold", 2.0)
        self.declare_parameter("confirm_duration_s", 1.0)
        self.declare_parameter("voltage_topic", "/charging/voltage")
        self.declare_parameter("contact_topic", "/docking/contact_confirmed")

        self._threshold = self.get_parameter("voltage_threshold").value
        self._confirm_duration = self.get_parameter("confirm_duration_s").value

        voltage_topic = (
            self.get_parameter("voltage_topic").get_parameter_value().string_value
        )
        contact_topic = (
            self.get_parameter("contact_topic").get_parameter_value().string_value
        )

        self._contact_pub = self.create_publisher(Bool, contact_topic, 10)
        self._voltage_sub = self.create_subscription(
            Float32, voltage_topic, self._on_voltage, 10
        )

        self._contact_start_time: Optional[float] = None
        self._confirmed = False

        self.get_logger().info(
            f"Contact detector: threshold={self._threshold}V, "
            f"confirm={self._confirm_duration}s"
        )

    def _on_voltage(self, msg: Float32) -> None:
        now = self.get_clock().now().nanoseconds / 1e9

        if msg.data >= self._threshold:
            if self._contact_start_time is None:
                self._contact_start_time = now

            elapsed = now - self._contact_start_time
            if elapsed >= self._confirm_duration and not self._confirmed:
                self._confirmed = True
                self.get_logger().info(f"Contact confirmed (voltage={msg.data:.2f}V)")
        else:
            self._contact_start_time = None
            if self._confirmed:
                self._confirmed = False
                self.get_logger().warn("Contact lost")

        contact_msg = Bool()
        contact_msg.data = self._confirmed
        self._contact_pub.publish(contact_msg)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = ContactDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
