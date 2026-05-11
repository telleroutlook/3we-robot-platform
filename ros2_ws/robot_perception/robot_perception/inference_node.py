# SPDX-License-Identifier: Apache-2.0
"""Hailo AI accelerator inference node for object detection."""

import threading
import time

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
        self.declare_parameter("nms_threshold", 0.45)
        self.declare_parameter("device_id", 0)
        self.declare_parameter("input_topic", "/camera/image_raw")
        self.declare_parameter("output_topic", "/perception/detections")
        self.declare_parameter("input_width", 640)
        self.declare_parameter("input_height", 640)

        self._model_path = (
            self.get_parameter("model_path").get_parameter_value().string_value
        )
        self._confidence_threshold = (
            self.get_parameter("confidence_threshold")
            .get_parameter_value()
            .double_value
        )
        self._nms_threshold = (
            self.get_parameter("nms_threshold").get_parameter_value().double_value
        )
        self._device_id = (
            self.get_parameter("device_id").get_parameter_value().integer_value
        )
        input_topic = (
            self.get_parameter("input_topic").get_parameter_value().string_value
        )
        output_topic = (
            self.get_parameter("output_topic").get_parameter_value().string_value
        )
        self._input_width = (
            self.get_parameter("input_width").get_parameter_value().integer_value
        )
        self._input_height = (
            self.get_parameter("input_height").get_parameter_value().integer_value
        )

        self._bridge = CvBridge()
        self._latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._hailo_available = False
        self._hef_model = None
        self._vdevice = None
        self._configured_network = None
        self._input_vstream_info = None
        self._output_vstream_info = None
        self._pipeline = None
        self._passthrough_log_counter = 0

        # Attempt to import Hailo runtime
        try:
            from hailo_platform import (  # noqa: F401
                HEF,
                VDevice,
                ConfigureParams,
                HailoStreamInterface,
                InferVStreams,
                InputVStreamParams,
                OutputVStreamParams,
                FormatType,
            )

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
            from hailo_platform import (
                HEF,
                VDevice,
                ConfigureParams,
                InputVStreamParams,
                OutputVStreamParams,
                FormatType,
            )

            self.get_logger().info(f"Loading model: {self._model_path}")
            self._hef_model = HEF(self._model_path)
            params = VDevice.create_params()
            params.device_ids = [self._device_id]
            self._vdevice = VDevice(params)

            configure_params = ConfigureParams.create_from_hef(
                self._hef_model, interface=ConfigureParams.default_interface()
            )
            self._configured_network = self._vdevice.configure(
                self._hef_model, configure_params
            )[0]

            self._input_vstream_info = self._hef_model.get_input_vstream_infos()
            self._output_vstream_info = self._hef_model.get_output_vstream_infos()

            self._input_vstream_params = InputVStreamParams.make_from_network_group(
                self._configured_network,
                quantized=False,
                format_type=FormatType.FLOAT32,
            )
            self._output_vstream_params = OutputVStreamParams.make_from_network_group(
                self._configured_network,
                quantized=False,
                format_type=FormatType.FLOAT32,
            )

            input_shape = self._input_vstream_info[0].shape
            self._input_height = input_shape[1]
            self._input_width = input_shape[2]

            # Open the inference pipeline once (DMA buffers + stream threads)
            # and reuse across all frames for the lifetime of the node.
            from hailo_platform import InferVStreams

            self._pipeline = InferVStreams(
                self._configured_network,
                self._input_vstream_params,
                self._output_vstream_params,
            )
            self._pipeline.__enter__()

            self.get_logger().info(
                f"Hailo model loaded (input: {self._input_width}x{self._input_height}, "
                f"outputs: {len(self._output_vstream_info)})"
            )
        except Exception as e:
            self.get_logger().error(f"Failed to initialize Hailo device: {e}")
            self._hailo_available = False

    def _image_callback(self, msg: Image) -> None:
        """Store the latest camera frame."""
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        with self._frame_lock:
            self._latest_frame = frame

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Resize and normalize frame for model input."""
        import cv2

        h, w = frame.shape[:2]
        target_h, target_w = self._input_height, self._input_width

        # Letterbox resize preserving aspect ratio
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to target dimensions
        padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        pad_top = (target_h - new_h) // 2
        pad_left = (target_w - new_w) // 2
        padded[pad_top : pad_top + new_h, pad_left : pad_left + new_w] = resized

        self._pad_info = (scale, pad_left, pad_top)
        return padded.astype(np.float32) / 255.0

    def _postprocess(
        self, raw_output: dict, img_width: int, img_height: int
    ) -> list[tuple[str, float, float, float, float, float]]:
        """Parse raw output tensors into detections with NMS."""
        detections: list[tuple[str, float, float, float, float, float]] = []

        # Hailo YOLO models output detection tensors
        # Format depends on model but typically: [batch, num_detections, 5+num_classes]
        # or multiple scale outputs that need to be concatenated
        output_tensors = list(raw_output.values())

        if not output_tensors:
            return detections

        # Handle single concatenated output (common for compiled YOLOv8)
        raw = output_tensors[0]
        if raw.ndim == 3:
            raw = raw[0]  # Remove batch dimension

        # YOLOv8 output format: [num_detections, 4+num_classes] or transposed
        if raw.shape[0] < raw.shape[1]:
            raw = raw.T  # Transpose to [num_detections, features]

        if raw.shape[1] < 5:
            # Multi-output model: try to concatenate all outputs
            all_outputs = []
            for tensor in output_tensors:
                t = tensor[0] if tensor.ndim == 3 else tensor
                if t.shape[0] < t.shape[1]:
                    t = t.T
                all_outputs.append(t)
            if all_outputs:
                raw = np.concatenate(all_outputs, axis=0)

        num_features = raw.shape[1]
        if num_features < 5:
            return detections

        # Extract boxes and class scores
        # YOLOv8: [cx, cy, w, h, class_scores...]
        boxes = raw[:, :4]
        class_scores = raw[:, 4:]

        # Get max class score and class ID per detection
        max_scores = np.max(class_scores, axis=1)
        class_ids = np.argmax(class_scores, axis=1)

        # Confidence filter
        mask = max_scores > self._confidence_threshold
        boxes = boxes[mask]
        max_scores = max_scores[mask]
        class_ids = class_ids[mask]

        if len(boxes) == 0:
            return detections

        # Convert from model coords to pixel coords (undo letterbox)
        scale, pad_left, pad_top = self._pad_info

        cx = (boxes[:, 0] * self._input_width - pad_left) / scale
        cy = (boxes[:, 1] * self._input_height - pad_top) / scale
        w = boxes[:, 2] * self._input_width / scale
        h = boxes[:, 3] * self._input_height / scale

        # NMS
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        indices = self._nms(x1, y1, x2, y2, max_scores, self._nms_threshold)

        for idx in indices:
            detections.append(
                (
                    str(int(class_ids[idx])),
                    float(max_scores[idx]),
                    float(cx[idx]),
                    float(cy[idx]),
                    float(w[idx]),
                    float(h[idx]),
                )
            )

        return detections

    @staticmethod
    def _nms(
        x1: np.ndarray,
        y1: np.ndarray,
        x2: np.ndarray,
        y2: np.ndarray,
        scores: np.ndarray,
        threshold: float,
    ) -> list[int]:
        """Non-maximum suppression."""
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep: list[int] = []

        while order.size > 0:
            i = order[0]
            keep.append(int(i))

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

            inds = np.where(iou <= threshold)[0]
            order = order[inds + 1]

        return keep

    def _inference_callback(self) -> None:
        """Run inference on the latest frame."""
        if not self._hailo_available:
            self._passthrough_log_counter += 1
            if self._passthrough_log_counter % 150 == 1:
                self.get_logger().info(
                    "Hailo runtime not found, running in passthrough mode"
                )
            return

        with self._frame_lock:
            frame = self._latest_frame
        if frame is None:
            return

        if self._configured_network is None:
            return

        t_start = time.perf_counter()

        # Preprocess
        img_h, img_w = frame.shape[:2]
        input_data = self._preprocess(frame)
        input_data = np.expand_dims(input_data, axis=0)  # Add batch dim

        # Run inference via persistent pipeline
        try:
            input_name = self._input_vstream_info[0].name
            input_dict = {input_name: input_data}
            raw_output = self._pipeline.infer(input_dict)

        except Exception as e:
            self.get_logger().error(f"Inference failed: {e}", throttle_duration_sec=5.0)
            return

        # Postprocess
        detections = self._postprocess(raw_output, img_w, img_h)

        # Build and publish Detection2DArray
        detections_msg = Detection2DArray()
        detections_msg.header.stamp = self.get_clock().now().to_msg()
        detections_msg.header.frame_id = "camera_link"

        for class_id, score, cx, cy, w, h in detections:
            det = self._make_detection(class_id, score, cx, cy, w, h)
            detections_msg.detections.append(det)

        self._detection_pub.publish(detections_msg)

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        if len(detections) > 0:
            self.get_logger().debug(
                f"Inference: {t_elapsed_ms:.1f}ms, {len(detections)} detections",
                throttle_duration_sec=1.0,
            )

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

    def destroy_node(self) -> None:
        """Release Hailo device resources before node destruction."""
        if self._pipeline is not None:
            try:
                self._pipeline.__exit__(None, None, None)
            except Exception as exc:
                self.get_logger().warning(f"Failed to close Hailo pipeline: {exc}")
            self._pipeline = None
        if self._vdevice is not None:
            try:
                self._vdevice.release()
            except Exception as exc:
                self.get_logger().warning(f"Failed to release Hailo VDevice: {exc}")
            self._vdevice = None
        super().destroy_node()


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
