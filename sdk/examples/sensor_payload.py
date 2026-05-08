#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Example: Sensor payload publishing data to ROS2.

This demonstrates a payload that reads sensor data via PBC-34
and publishes it as a ROS2 topic.
"""

import sys
import time
sys.path.insert(0, '..')

from payload_interface.payload_protocol import PayloadInterface

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Temperature
except ImportError:
    print("ROS2 (rclpy) not available. Install ros-humble-desktop or source your workspace.")
    sys.exit(1)


CMD_READ_TEMPERATURE = 0x10


class SensorPayloadNode(Node):
    """ROS2 node that reads temperature from a PBC-34 sensor payload."""

    def __init__(self):
        super().__init__('sensor_payload')
        self.publisher = self.create_publisher(Temperature, '/payload/temperature', 10)
        self.timer = self.create_timer(1.0, self.timer_callback)

        self.interface = PayloadInterface(i2c_bus=1)
        descriptor = self.interface.discover()

        if descriptor is None:
            self.get_logger().error("No payload detected on PBC-34")
            raise RuntimeError("Payload not found")

        self.get_logger().info(f"Connected to payload: {descriptor.name}")

    def timer_callback(self):
        response = self.interface.send_command(CMD_READ_TEMPERATURE)
        if response is None or len(response) < 3:
            self.get_logger().warn("Failed to read temperature from payload")
            return

        # Parse response: [CMD_ACK, TEMP_INT, TEMP_FRAC]
        temp_int = response[1]
        temp_frac = response[2]
        temperature = float(temp_int) + float(temp_frac) / 100.0

        msg = Temperature()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'payload_mount_link'
        msg.temperature = temperature
        msg.variance = 0.5

        self.publisher.publish(msg)
        self.get_logger().debug(f"Temperature: {temperature:.2f}°C")

    def destroy_node(self):
        self.interface.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = SensorPayloadNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
