# SPDX-License-Identifier: Apache-2.0
"""Traditional CV ball detector — HSV filtering + HoughCircles.

Designed as a Hailo-free fallback for Standard-C and Basic SKUs.
Publishes the same Detection2DArray interface as inference_node.py so
downstream consumers (ball_tracker) work without modification.
"""

from __future__ import annotations

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import (
    Detection2D,
    Detection2DArray,
    ObjectHypothesisWithPose,
)
from cv_bridge import CvBridge

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


class BallDetectorNode(Node):
    """Detect ping-pong balls using color filtering and circle detection."""

    def __init__(self) -> None:
        super().__init__("ball_detector")

        self.declare_parameter("input_topic", "/camera/image_raw")
        self.declare_parameter("output_topic", "/perception/detections")
        self.declare_parameter("hsv_lower_orange", [5, 100, 100])
        self.declare_parameter("hsv_upper_orange", [25, 255, 255])
        self.declare_parameter("hsv_lower_white", [0, 0, 200])
        self.declare_parameter("hsv_upper_white", [180, 30, 255])
        self.declare_parameter("min_radius", 8)
        self.declare_parameter("max_radius", 40)
        self.declare_parameter("confidence_threshold", 0.6)
        self.declare_parameter("ball_class_id", "ping_pong_ball")

        input_topic = self.get_parameter("input_topic").value
        output_topic = self.get_parameter("output_topic").value

        self._bridge = CvBridge()
        self._sub = self.create_subscription(Image, input_topic, self._on_image, 10)
        self._pub = self.create_publisher(Detection2DArray, output_topic, 10)

        self.get_logger().info(
            f"Ball detector started: {input_topic} -> {output_topic}"
        )

    def _on_image(self, msg: Image) -> None:
        if cv2 is None:
            return

        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        detections = self._detect_balls(frame)

        det_array = Detection2DArray()
        det_array.header = msg.header
        det_array.detections = detections
        self._pub.publish(det_array)

    def _detect_balls(self, frame: np.ndarray) -> list[Detection2D]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]

        hsv_lower_orange = np.array(
            self.get_parameter("hsv_lower_orange").value, dtype=np.uint8
        )
        hsv_upper_orange = np.array(
            self.get_parameter("hsv_upper_orange").value, dtype=np.uint8
        )
        hsv_lower_white = np.array(
            self.get_parameter("hsv_lower_white").value, dtype=np.uint8
        )
        hsv_upper_white = np.array(
            self.get_parameter("hsv_upper_white").value, dtype=np.uint8
        )

        mask_orange = cv2.inRange(hsv, hsv_lower_orange, hsv_upper_orange)
        mask_white = cv2.inRange(hsv, hsv_lower_white, hsv_upper_white)
        mask = cv2.bitwise_or(mask_orange, mask_white)

        mask = cv2.GaussianBlur(mask, (9, 9), 2)

        min_r = self.get_parameter("min_radius").value
        max_r = self.get_parameter("max_radius").value
        confidence_threshold = self.get_parameter("confidence_threshold").value
        ball_class_id = self.get_parameter("ball_class_id").value

        circles = cv2.HoughCircles(
            mask,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=float(min_r * 2),
            param1=50,
            param2=30,
            minRadius=min_r,
            maxRadius=max_r,
        )

        detections: list[Detection2D] = []
        if circles is None:
            return detections

        for circle in np.round(circles[0]).astype(int):
            cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])

            roi_mask = mask[
                max(0, cy - r) : min(h, cy + r),
                max(0, cx - r) : min(w, cx + r),
            ]
            if roi_mask.size == 0:
                continue
            fill_ratio = float(np.count_nonzero(roi_mask)) / roi_mask.size
            confidence = min(1.0, fill_ratio * 1.3)

            if confidence < confidence_threshold:
                continue

            det = Detection2D()
            det.bbox.center.position.x = float(cx)
            det.bbox.center.position.y = float(cy)
            det.bbox.size_x = float(r * 2)
            det.bbox.size_y = float(r * 2)

            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = ball_class_id
            hyp.hypothesis.score = confidence
            det.results.append(hyp)

            detections.append(det)

        return detections


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = BallDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
