# SPDX-License-Identifier: Apache-2.0
"""Ball tracker node — filters Detection2DArray for ping-pong balls and
estimates 3D position in base_link frame using known ball diameter.

Subscribes: /perception/detections (Detection2DArray)
Publishes:  /collection/ball_target (PoseStamped) — closest confirmed ball
            /collection/balls_visible (UInt8)
"""

from __future__ import annotations

from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import UInt8
from vision_msgs.msg import Detection2DArray


class BallTrackerNode(Node):
    """Filter detections for ping-pong balls and publish tracking target."""

    def __init__(self) -> None:
        super().__init__("ball_tracker")

        self.declare_parameter("ball_class_id", "ping_pong_ball")
        self.declare_parameter("min_confidence", 0.6)
        self.declare_parameter("min_consecutive_frames", 3)
        self.declare_parameter("ball_diameter_m", 0.04)
        self.declare_parameter("camera_frame", "camera_link")
        self.declare_parameter("detection_topic", "/perception/detections")
        self.declare_parameter("focal_length_px", 500.0)

        detection_topic = self.get_parameter("detection_topic").value

        self._sub = self.create_subscription(
            Detection2DArray, detection_topic, self._on_detections, 10
        )
        self._target_pub = self.create_publisher(
            PoseStamped, "/collection/ball_target", 10
        )
        self._count_pub = self.create_publisher(UInt8, "/collection/balls_visible", 10)

        self._consecutive_counts: dict[str, int] = {}
        self._last_target: Optional[PoseStamped] = None

        self.get_logger().info("Ball tracker started")

    def _on_detections(self, msg: Detection2DArray) -> None:
        ball_class_id = self.get_parameter("ball_class_id").value
        min_confidence = self.get_parameter("min_confidence").value
        min_frames = self.get_parameter("min_consecutive_frames").value

        balls = []
        for det in msg.detections:
            for result in det.results:
                if (
                    result.hypothesis.class_id == ball_class_id
                    and result.hypothesis.score >= min_confidence
                ):
                    balls.append(det)
                    break

        count_msg = UInt8()
        count_msg.data = min(len(balls), 255)
        self._count_pub.publish(count_msg)

        if not balls:
            self._consecutive_counts.clear()
            return

        closest = min(
            balls,
            key=lambda d: self._estimate_depth(d.bbox.size_x),
        )

        key = f"{int(closest.bbox.center.position.x)}_{int(closest.bbox.center.position.y)}"
        self._consecutive_counts[key] = self._consecutive_counts.get(key, 0) + 1

        stale_keys = [k for k in self._consecutive_counts if k != key]
        for k in stale_keys:
            self._consecutive_counts.pop(k, None)

        if self._consecutive_counts[key] >= min_frames:
            target = self._detection_to_pose(closest, msg.header)
            self._target_pub.publish(target)
            self._last_target = target

    def _estimate_depth(self, bbox_size_px: float) -> float:
        ball_diameter_m = self.get_parameter("ball_diameter_m").value
        focal_length_px = self.get_parameter("focal_length_px").value
        if bbox_size_px <= 0:
            return 999.0
        return (ball_diameter_m * focal_length_px) / bbox_size_px

    def _detection_to_pose(self, det, header) -> PoseStamped:
        camera_frame = self.get_parameter("camera_frame").value
        depth = self._estimate_depth(det.bbox.size_x)

        focal_length_px = self.get_parameter("focal_length_px").value
        cx = det.bbox.center.position.x
        cy = det.bbox.center.position.y

        pose = PoseStamped()
        pose.header.stamp = header.stamp
        pose.header.frame_id = camera_frame
        pose.pose.position.x = depth
        pose.pose.position.y = -(cx - 320.0) * depth / focal_length_px
        pose.pose.position.z = -(cy - 240.0) * depth / focal_length_px
        pose.pose.orientation.w = 1.0
        return pose


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = BallTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
