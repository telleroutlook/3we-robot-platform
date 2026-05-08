#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Encoder calibration — log encoder counts to verify CPR and direction."""

import rclpy
from rclpy.node import Node
from robot_interfaces.msg import WheelSpeeds
import time
import sys


class EncoderCalibrate(Node):
    def __init__(self):
        super().__init__("encoder_calibrate")
        self.sub = self.create_subscription(
            WheelSpeeds, "/wheel_speeds", self.wheel_cb, 10
        )
        self.latest = None
        self.samples = []
        self.get_logger().info(
            "Encoder calibration ready — rotate wheels manually or run motors"
        )

    def wheel_cb(self, msg: WheelSpeeds):
        self.latest = msg
        self.samples.append(
            {
                "time": time.time(),
                "fl": msg.front_left,
                "fr": msg.front_right,
                "rl": msg.rear_left,
                "rr": msg.rear_right,
            }
        )

    def record(self, duration: float):
        self.samples = []
        self.get_logger().info(f"Recording for {duration}s...")
        start = time.time()
        while time.time() - start < duration:
            rclpy.spin_once(self, timeout_sec=0.05)

        self.get_logger().info(f"Collected {len(self.samples)} samples")
        if self.samples:
            for wheel in ["fl", "fr", "rl", "rr"]:
                speeds = [s[wheel] for s in self.samples]
                avg = sum(speeds) / len(speeds)
                peak = max(abs(s) for s in speeds)
                self.get_logger().info(
                    f"  {wheel.upper()}: avg={avg:.3f} RPS, peak={peak:.3f} RPS"
                )


def main():
    rclpy.init()
    node = EncoderCalibrate()

    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0

    try:
        node.record(duration)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
