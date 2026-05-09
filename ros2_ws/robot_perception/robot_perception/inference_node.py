# SPDX-License-Identifier: Apache-2.0
"""Hailo AI accelerator inference node for object detection."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from cv_bridge import CvBridge

import numpy as np


class HailoInferenceNode(Node):
    """ROS2 node that runs object detection inference on the Hailo AI accelerator."""

    def __init__(self) -> None:
        super().__init__("hailo_inference")

        # Declare parameters
        self.declare_parameter("model_path", "")
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("device_id", 0)
        self.declare_parameter("input_topic", "/camera/image_raw")
        self.declare_parameter("output_topic", "/perception/detections")

        self._model_path = self.get_parameter("model_path").get_parameter_value().string_value
        self._confidence_threshold = self.get_parameter("confidence_threshold").get_parameter_value().double_value
        self._device_id = self.get_parameter("device_id").get_parameter_value().integer_value
        input_topic = self.get_parameter("input_topic").get_parameter_value().string_value
        output_topic = self.get_parameter("output_topic").get_parameter_value().string_value

        self._bridge = CvBridge()
        self._latest_frame: np.ndarray | None = None
        self._hailo_available = False
        self._hef_model = None
        self._passthrough_log_counter = 0

        # Attempt to import Hailo runtime
        try:
            from hailo_platform import HEF, VDevice, ConfigureParams, HailoStreamInterface  # noqa: F401

            self._hailo_available = True
            self.get_logger().info("Hailo runtime detected successfully")
        except ImportError:
            self._hailo_available = False
            self.get_logger().warning(
                "hailo_platform not found. Running in passthrough mode. "
                "Install HailoRT and hailo_platform to enable inference."
            )

        # Initialize Hailo device and model if available
        if self._hailo_available and self._model_path:
            self._initialize_hailo()

        # Subscriber for camera images
        self._image_sub = self.create_subscription(
            Image, input_topic, self._image_callback, 10
        )

        # Publisher for detections
        self._detection_pub = self.create_publisher(Detection2DArray, output_topic, 10)

        # Inference timer at 30 Hz
        self._timer = self.create_timer(1.0 / 30.0, self._inference_callback)

        self.get_logger().info(
            f"HailoInferenceNode initialized (hailo_available={self._hailo_available})"
        )

    def _initialize_hailo(self) -> None:
        """Load the HEF model onto the Hailo device."""
        try:
            from hailo_platform import HEF, VDevice, ConfigureParams, HailoStreamInterface  # noqa: F401

            self.get_logger().info(f"Loading model: {self._model_path}")
            self._hef_model = HEF(self._model_path)
            params = VDevice.create_params()
            params.device_ids = [self._device_id]
            self._vdevice = VDevice(params)
            self._infer_model = self._vdevice.configure(self._hef_model, ConfigureParams.create_from_hef(self._hef_model))
            self.get_logger().info("Hailo model loaded and device configured")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize Hailo device: {e}")
            self._hailo_available = False

    def _image_callback(self, msg: Image) -> None:
        """Store the latest camera frame."""
        self._latest_frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")

    def _inference_callback(self) -> None:
        """Run inference on the latest frame or log passthrough status."""
        if not self._hailo_available:
            self._passthrough_log_counter += 1
            if self._passthrough_log_counter % 150 == 1:
                self.get_logger().info("Hailo runtime not found, running in passthrough mode")
            return

        if self._latest_frame is None:
            return

        if self._hef_model is None:
            return

        # Run inference and publish detections
        detections_msg = Detection2DArray()
        detections_msg.header.stamp = self.get_clock().now().to_msg()
        detections_msg.header.frame_id = "camera_link"

        # Placeholder: actual inference pipeline populates detections here
        # In production, preprocess frame -> run on Hailo -> postprocess NMS results
        self._detection_pub.publish(detections_msg)

    def _make_detection(
        self, class_id: str, score: float, cx: float, cy: float, w: float, h: float
    ) -> Detection2D:
        """Create a Detection2D message from inference results."""
        det = Detection2D()
        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id = class_id
        hypothesis.hypothesis.score = score
        det.results.append(hypothesis)
        det.bbox.center.position.x = cx
        det.bbox.center.position.y = cy
        det.bbox.size_x = w
        det.bbox.size_y = h
        return det


def main(args=None) -> None:
    """Entry point for ros2 run."""
    rclpy.init(args=args)
    node = HailoInferenceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
