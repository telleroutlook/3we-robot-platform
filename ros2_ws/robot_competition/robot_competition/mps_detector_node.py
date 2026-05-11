# SPDX-License-Identifier: Apache-2.0
"""MPS (Machine Processing Station) light signal detector for RCLL."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MpsDetectorNode(Node):
    """Detects MPS machine light signals using camera + YOLO inference."""

    def __init__(self):
        super().__init__("mps_detector")
        self.declare_parameter("model_path", "")
        self.declare_parameter("confidence_threshold", 0.7)
        self.declare_parameter("camera_topic", "/camera/image_raw")

        self.detection_pub = self.create_publisher(
            String, "/competition/mps_detections", 10
        )

        # TODO: Subscribe to camera image topic
        # TODO: Load YOLO model for MPS light pattern recognition
        # TODO: Classify light states: RED, YELLOW, GREEN, OFF
        # TODO: Determine machine type from light sequence
        # TODO: Publish detected machine states with position

        self.get_logger().info("MPS detector node initialized (stub)")


def main(args=None):
    rclpy.init(args=args)
    node = MpsDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
