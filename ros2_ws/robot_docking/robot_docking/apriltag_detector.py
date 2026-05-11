# SPDX-License-Identifier: Apache-2.0
"""
AprilTag detection node for docking visual servoing.

Detects AprilTag 36h11 markers from camera images and publishes their
6-DOF pose relative to the camera frame. The visual_servo node subscribes
to /docking/tag_pose for closed-loop alignment control.

Supports both the 'apriltag' (dt-apriltags) and 'pupil-apriltags' Python
packages, with graceful fallback to passthrough mode if neither is available.
"""

from typing import Optional

import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, Quaternion
from cv_bridge import CvBridge


class AprilTagDetectorNode(Node):
    """Detects AprilTag markers and publishes their pose."""

    def __init__(self) -> None:
        super().__init__("apriltag_detector")

        self.declare_parameter("tag_family", "tag36h11")
        self.declare_parameter("tag_size_m", 0.16)
        self.declare_parameter("target_tag_id", 0)
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/camera_info")
        self.declare_parameter("output_topic", "/docking/tag_pose")
        self.declare_parameter("detection_rate_hz", 15.0)

        self._tag_family = self.get_parameter("tag_family").value
        self._tag_size = self.get_parameter("tag_size_m").value
        self._target_tag_id = self.get_parameter("target_tag_id").value
        image_topic = self.get_parameter("image_topic").value
        camera_info_topic = self.get_parameter("camera_info_topic").value
        output_topic = self.get_parameter("output_topic").value
        detection_rate = self.get_parameter("detection_rate_hz").value

        self._bridge = CvBridge()
        self._camera_params: Optional[tuple[float, float, float, float]] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._detector = None
        self._available = False

        self._init_detector()

        self._image_sub = self.create_subscription(
            Image, image_topic, self._image_callback, 10
        )
        self._info_sub = self.create_subscription(
            CameraInfo, camera_info_topic, self._camera_info_callback, 10
        )
        self._pose_pub = self.create_publisher(PoseStamped, output_topic, 10)

        self._timer = self.create_timer(1.0 / detection_rate, self._detect_callback)

        self.get_logger().info(
            f"AprilTag detector initialized (family={self._tag_family}, "
            f"target_id={self._target_tag_id}, available={self._available})"
        )

    def _init_detector(self) -> None:
        """Initialize the AprilTag detector library."""
        try:
            from dt_apriltags import Detector

            self._detector = Detector(
                families=self._tag_family,
                nthreads=2,
                quad_decimate=2.0,
                quad_sigma=0.0,
                decode_sharpening=0.25,
            )
            self._available = True
            self.get_logger().info("Using dt-apriltags detector")
            return
        except ImportError:
            pass

        try:
            import pupil_apriltags

            self._detector = pupil_apriltags.Detector(
                families=self._tag_family,
                nthreads=2,
                quad_decimate=2.0,
                quad_sigma=0.0,
                decode_sharpening=0.25,
            )
            self._available = True
            self.get_logger().info("Using pupil-apriltags detector")
            return
        except ImportError:
            pass

        self._available = False
        self.get_logger().warning(
            "No apriltag library found (dt-apriltags or pupil-apriltags). "
            "Install one to enable tag detection."
        )

    def _image_callback(self, msg: Image) -> None:
        """Store the latest camera frame."""
        self._latest_frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="mono8")

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        """Extract camera intrinsics from CameraInfo."""
        if self._camera_params is not None:
            return
        k = msg.k
        fx, fy, cx, cy = k[0], k[4], k[2], k[5]
        self._camera_params = (fx, fy, cx, cy)
        self.get_logger().info(
            f"Camera params: fx={fx:.1f}, fy={fy:.1f}, cx={cx:.1f}, cy={cy:.1f}"
        )

    def _detect_callback(self) -> None:
        """Run AprilTag detection on the latest frame."""
        if not self._available or self._latest_frame is None:
            return
        if self._camera_params is None:
            return

        frame = self._latest_frame
        fx, fy, cx, cy = self._camera_params

        detections = self._detector.detect(
            frame,
            estimate_tag_pose=True,
            camera_params=(fx, fy, cx, cy),
            tag_size=self._tag_size,
        )

        for det in detections:
            if det.tag_id != self._target_tag_id:
                continue

            if det.pose_R is None or det.pose_t is None:
                continue

            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = "camera_link"

            t = det.pose_t.flatten()
            pose_msg.pose.position.x = float(t[2])
            pose_msg.pose.position.y = float(-t[0])
            pose_msg.pose.position.z = float(-t[1])

            pose_msg.pose.orientation = self._rotation_matrix_to_quaternion(det.pose_R)

            self._pose_pub.publish(pose_msg)
            return

    @staticmethod
    def _rotation_matrix_to_quaternion(r: np.ndarray) -> Quaternion:
        """Convert a 3x3 rotation matrix to a ROS Quaternion message."""
        trace = r[0, 0] + r[1, 1] + r[2, 2]
        q = Quaternion()

        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            q.w = 0.25 / s
            q.x = (r[2, 1] - r[1, 2]) * s
            q.y = (r[0, 2] - r[2, 0]) * s
            q.z = (r[1, 0] - r[0, 1]) * s
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            s = 2.0 * np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
            q.w = (r[2, 1] - r[1, 2]) / s
            q.x = 0.25 * s
            q.y = (r[0, 1] + r[1, 0]) / s
            q.z = (r[0, 2] + r[2, 0]) / s
        elif r[1, 1] > r[2, 2]:
            s = 2.0 * np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
            q.w = (r[0, 2] - r[2, 0]) / s
            q.x = (r[0, 1] + r[1, 0]) / s
            q.y = 0.25 * s
            q.z = (r[1, 2] + r[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
            q.w = (r[1, 0] - r[0, 1]) / s
            q.x = (r[0, 2] + r[2, 0]) / s
            q.y = (r[1, 2] + r[2, 1]) / s
            q.z = 0.25 * s

        return q


def main(args=None) -> None:
    """Entry point for ros2 run."""
    rclpy.init(args=args)
    node = AprilTagDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
