# SPDX-License-Identifier: Apache-2.0
"""
ROS2 diagnostics aggregator node for the 3WE Robot Platform.

Subscribes to platform health topics and publishes a unified
DiagnosticArray at 1 Hz for monitoring, alerting, and fleet management.
"""

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool


class DiagnosticsNode(Node):
    def __init__(self) -> None:
        super().__init__("robot_diagnostics")

        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("robot_id", "")

        rate = self.get_parameter("publish_rate_hz").value
        if rate <= 0.0:
            raise ValueError(f"publish_rate_hz must be positive, got {rate}")
        self._robot_id = (
            self.get_parameter("robot_id").value or self._get_default_robot_id()
        )

        self._start_time = time.monotonic()
        self._battery_state: BatteryState | None = None
        self._estop_active = False
        self._topic_rates: dict[str, float] = {}
        self._topic_last_time: dict[str, float] = {}
        self._topic_count: dict[str, int] = {}

        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=10,
        )

        self.create_subscription(
            BatteryState, "/battery_state", self._on_battery, reliable_qos
        )
        self.create_subscription(
            Bool, "/emergency_stop_state", self._on_estop, reliable_qos
        )

        self._diag_pub = self.create_publisher(
            DiagnosticArray, "/diagnostics", reliable_qos
        )

        period = 1.0 / rate
        self.create_timer(period, self._publish_diagnostics)

        self.get_logger().info(
            f"Diagnostics node started (robot_id={self._robot_id}, rate={rate}Hz)"
        )

    def _get_default_robot_id(self) -> str:
        return self.get_namespace().strip("/") or "robot"

    def _on_battery(self, msg: BatteryState) -> None:
        self._battery_state = msg
        self._record_topic_rate("/battery_state")

    def _on_estop(self, msg: Bool) -> None:
        self._estop_active = msg.data
        self._record_topic_rate("/emergency_stop_state")

    def _record_topic_rate(self, topic: str) -> None:
        now = time.monotonic()
        self._topic_count[topic] = self._topic_count.get(topic, 0) + 1

        last = self._topic_last_time.get(topic)
        if last is not None:
            dt = now - last
            if dt > 0:
                alpha = 0.3
                prev_rate = self._topic_rates.get(topic, 1.0 / dt)
                self._topic_rates[topic] = (
                    alpha * (1.0 / dt) + (1.0 - alpha) * prev_rate
                )
        self._topic_last_time[topic] = now

    def _publish_diagnostics(self) -> None:
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()

        msg.status.append(self._build_system_status())
        msg.status.append(self._build_battery_status())
        msg.status.append(self._build_safety_status())
        msg.status.append(self._build_topics_status())

        self._diag_pub.publish(msg)

    def _build_system_status(self) -> DiagnosticStatus:
        uptime = time.monotonic() - self._start_time
        status = DiagnosticStatus()
        status.name = f"{self._robot_id}/system"
        status.level = DiagnosticStatus.OK
        status.message = "Running"
        status.values = [
            KeyValue(key="uptime_s", value=f"{uptime:.1f}"),
            KeyValue(key="robot_id", value=self._robot_id),
        ]
        return status

    def _build_battery_status(self) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = f"{self._robot_id}/battery"

        if self._battery_state is None:
            status.level = DiagnosticStatus.STALE
            status.message = "No battery data received"
            return status

        raw_pct = self._battery_state.percentage
        pct = raw_pct * 100.0 if raw_pct <= 1.0 else raw_pct
        voltage = self._battery_state.voltage

        if pct < 10.0:
            status.level = DiagnosticStatus.ERROR
            status.message = f"Critical: {pct:.0f}%"
        elif pct < 25.0:
            status.level = DiagnosticStatus.WARN
            status.message = f"Low: {pct:.0f}%"
        else:
            status.level = DiagnosticStatus.OK
            status.message = f"OK: {pct:.0f}%"

        status.values = [
            KeyValue(key="percentage", value=f"{pct:.1f}"),
            KeyValue(key="voltage_v", value=f"{voltage:.2f}"),
        ]
        return status

    def _build_safety_status(self) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = f"{self._robot_id}/safety"

        if self._estop_active:
            status.level = DiagnosticStatus.ERROR
            status.message = "E-STOP ACTIVE"
        else:
            status.level = DiagnosticStatus.OK
            status.message = "Normal operation"

        status.values = [
            KeyValue(key="estop_active", value=str(self._estop_active).lower()),
        ]
        return status

    def _build_topics_status(self) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = f"{self._robot_id}/topics"
        status.level = DiagnosticStatus.OK
        status.message = f"{len(self._topic_rates)} topics active"

        for topic, rate in self._topic_rates.items():
            status.values.append(KeyValue(key=f"{topic}_hz", value=f"{rate:.1f}"))
            status.values.append(
                KeyValue(
                    key=f"{topic}_count", value=str(self._topic_count.get(topic, 0))
                )
            )

        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DiagnosticsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
