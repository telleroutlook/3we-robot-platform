# SPDX-License-Identifier: Apache-2.0
"""Payload state bridge: subscribes to raw JSON from micro-ROS and publishes typed PayloadState."""

import json
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    from robot_interfaces.msg import PayloadState

    HAS_PAYLOAD_MSG = True
except ImportError:
    HAS_PAYLOAD_MSG = False


class PayloadMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__("payload_monitor")

        self._sub = self.create_subscription(
            String, "/payload/state_raw", self._on_raw_state, 10
        )

        if HAS_PAYLOAD_MSG:
            self._pub = self.create_publisher(PayloadState, "/payload/state", 10)
        else:
            self._pub = None
            self.get_logger().warn(
                "robot_interfaces not available — publishing raw only"
            )

        self._raw_pub = self.create_publisher(String, "/payload/state_json", 10)
        self.get_logger().info("Payload monitor started")

    def _on_raw_state(self, msg: String) -> None:
        self._raw_pub.publish(msg)

        if not HAS_PAYLOAD_MSG or self._pub is None:
            return

        try:
            data: dict[str, Any] = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn(f"Invalid JSON from firmware: {msg.data[:80]}")
            return

        state_msg = PayloadState()
        state_msg.header.stamp = self.get_clock().now().to_msg()
        state_msg.payload_id = data.get("id", "")
        state_msg.name = data.get("name", "")

        fw_state = data.get("state", "")
        state_msg.connected = fw_state not in ("absent", "removing")

        power_5v_ma = data.get("power_5v_ma", 0)
        power_12v_ma = data.get("power_12v_ma", 0)
        state_msg.power_5v_active = power_5v_ma > 0
        state_msg.power_12v_active = power_12v_ma > 0
        state_msg.power_vbat_active = False

        state_msg.current_5v = power_5v_ma / 1000.0
        state_msg.current_12v = power_12v_ma / 1000.0
        state_msg.power_consumption_watts = (
            power_5v_ma * 5.0 + power_12v_ma * 12.0
        ) / 1000.0

        state_map = {
            "absent": PayloadState.STATUS_IDLE,
            "detected": PayloadState.STATUS_IDLE,
            "identifying": PayloadState.STATUS_IDLE,
            "powering": PayloadState.STATUS_IDLE,
            "ready": PayloadState.STATUS_ACTIVE,
            "fault": PayloadState.STATUS_ERROR,
            "removing": PayloadState.STATUS_IDLE,
        }
        state_msg.status = state_map.get(fw_state, PayloadState.STATUS_IDLE)

        self._pub.publish(state_msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PayloadMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
