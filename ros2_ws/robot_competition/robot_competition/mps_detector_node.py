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

        self.get_logger().warn("MPS detector node awaiting implementation")


def main(args=None):
    rclpy.init(args=args)
    node = MpsDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
