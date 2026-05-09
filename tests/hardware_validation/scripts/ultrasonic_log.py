#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Ultrasonic sensor logger — record range readings for calibration."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
import time
import sys


class UltrasonicLog(Node):
    TOPICS = [
        "/ultrasonic/front",
        "/ultrasonic/back",
        "/ultrasonic/left",
        "/ultrasonic/right",
    ]

    def __init__(self):
        super().__init__("ultrasonic_log")
        self.readings = {t: [] for t in self.TOPICS}
        self.latest = {t: None for t in self.TOPICS}

        for topic in self.TOPICS:
            self.create_subscription(Range, topic, self._make_cb(topic), 10)

        self.get_logger().info("Ultrasonic logger ready — monitoring all 4 sensors")

    def _make_cb(self, topic: str):
        def cb(msg: Range):
            self.latest[topic] = msg.range
            self.readings[topic].append({"time": time.time(), "range": msg.range})

        return cb

    def record(self, duration: float):
        self.readings = {t: [] for t in self.TOPICS}
        self.get_logger().info(f"Recording for {duration}s...")
        start = time.time()
        while time.time() - start < duration:
            rclpy.spin_once(self, timeout_sec=0.05)

        self.get_logger().info("--- Results ---")
        for topic in self.TOPICS:
            samples = self.readings[topic]
            direction = topic.split("/")[-1]
            if samples:
                ranges = [s["range"] for s in samples]
                avg = sum(ranges) / len(ranges)
                mn = min(ranges)
                mx = max(ranges)
                self.get_logger().info(
                    f"  {direction:5s}: {len(samples)} samples, "
                    f"avg={avg:.3f}m, min={mn:.3f}m, max={mx:.3f}m"
                )
            else:
                self.get_logger().warning(
                    f"  {direction:5s}: NO DATA (sensor timeout?)"
                )


def main():
    rclpy.init()
    node = UltrasonicLog()

    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0

    try:
        node.record(duration)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
