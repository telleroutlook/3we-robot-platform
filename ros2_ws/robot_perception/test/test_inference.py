# SPDX-License-Identifier: Apache-2.0
"""Unit tests for HailoInferenceNode pure-function logic (NMS, preprocess, postprocess)."""

import sys
from unittest.mock import MagicMock

import numpy as np
import pytest


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self, *a, **kw):
        pass

    def declare_parameter(self, *a, **kw):
        pass

    def get_parameter(self, *a, **kw):
        return MagicMock()

    def create_publisher(self, *a, **kw):
        return MagicMock()

    def create_subscription(self, *a, **kw):
        return MagicMock()

    def create_timer(self, *a, **kw):
        return MagicMock()

    def get_clock(self):
        return MagicMock()

    def get_logger(self):
        return MagicMock()


# Patch sys.modules before importing
_rclpy_mock = MagicMock()
_node_mod = MagicMock()
_node_mod.Node = _FakeNode
sys.modules.setdefault("rclpy", _rclpy_mock)
sys.modules["rclpy.node"] = _node_mod
sys.modules.setdefault("sensor_msgs.msg", MagicMock())
sys.modules.setdefault("vision_msgs.msg", MagicMock())
sys.modules.setdefault("cv_bridge", MagicMock())


from robot_perception.inference_node import HailoInferenceNode  # noqa: E402


class TestNms:
    """Tests for the static _nms method."""

    def test_single_detection_kept(self):
        x1 = np.array([10.0])
        y1 = np.array([10.0])
        x2 = np.array([50.0])
        y2 = np.array([50.0])
        scores = np.array([0.9])
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.5)
        assert result == [0]

    def test_no_detections_returns_empty(self):
        empty = np.array([])
        result = HailoInferenceNode._nms(empty, empty, empty, empty, empty, 0.5)
        assert result == []

    def test_non_overlapping_boxes_all_kept(self):
        x1 = np.array([0.0, 100.0, 200.0])
        y1 = np.array([0.0, 100.0, 200.0])
        x2 = np.array([50.0, 150.0, 250.0])
        y2 = np.array([50.0, 150.0, 250.0])
        scores = np.array([0.9, 0.8, 0.7])
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.5)
        assert sorted(result) == [0, 1, 2]

    def test_fully_overlapping_boxes_highest_score_kept(self):
        x1 = np.array([10.0, 10.0, 10.0])
        y1 = np.array([10.0, 10.0, 10.0])
        x2 = np.array([50.0, 50.0, 50.0])
        y2 = np.array([50.0, 50.0, 50.0])
        scores = np.array([0.6, 0.9, 0.7])
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.5)
        assert result == [1]

    def test_partial_overlap_below_threshold_both_kept(self):
        # Two boxes with ~25% overlap (IoU < 0.5)
        x1 = np.array([0.0, 30.0])
        y1 = np.array([0.0, 0.0])
        x2 = np.array([50.0, 80.0])
        y2 = np.array([50.0, 50.0])
        scores = np.array([0.9, 0.8])
        # IoU = (20*50) / (50*50 + 50*50 - 20*50) = 1000/4000 = 0.25
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.5)
        assert sorted(result) == [0, 1]

    def test_strict_threshold_suppresses_more(self):
        x1 = np.array([0.0, 20.0])
        y1 = np.array([0.0, 0.0])
        x2 = np.array([50.0, 70.0])
        y2 = np.array([50.0, 50.0])
        scores = np.array([0.9, 0.8])
        # IoU = (30*50)/(50*50 + 50*50 - 30*50) = 1500/3500 ≈ 0.43
        # With threshold=0.3, this overlap exceeds threshold → suppress
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.3)
        assert result == [0]

    def test_ordering_by_score(self):
        x1 = np.array([0.0, 0.0])
        y1 = np.array([0.0, 0.0])
        x2 = np.array([50.0, 50.0])
        y2 = np.array([50.0, 50.0])
        scores = np.array([0.3, 0.9])
        result = HailoInferenceNode._nms(x1, y1, x2, y2, scores, 0.5)
        assert result[0] == 1


class TestPreprocess:
    """Tests for the _preprocess method."""

    @pytest.fixture
    def node(self):
        """Create a minimal node-like object with required attributes."""
        obj = object.__new__(HailoInferenceNode)
        obj._input_width = 640
        obj._input_height = 640
        obj._pad_info = None
        return obj

    def test_output_shape(self, node):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = node._preprocess(frame)
        assert result.shape == (640, 640, 3)

    def test_output_dtype_float32(self, node):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = node._preprocess(frame)
        assert result.dtype == np.float32

    def test_output_normalized_range(self, node):
        frame = np.full((480, 640, 3), 255, dtype=np.uint8)
        result = node._preprocess(frame)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_letterbox_preserves_aspect_ratio(self, node):
        frame = np.full((200, 400, 3), 200, dtype=np.uint8)
        node._preprocess(frame)
        scale, pad_left, pad_top = node._pad_info
        assert scale == pytest.approx(640.0 / 400.0, rel=1e-3)
        assert pad_top > 0  # height is smaller, needs top padding

    def test_square_input_no_padding(self, node):
        frame = np.full((640, 640, 3), 128, dtype=np.uint8)
        node._preprocess(frame)
        scale, pad_left, pad_top = node._pad_info
        assert scale == pytest.approx(1.0)
        assert pad_left == 0
        assert pad_top == 0

    def test_pad_fill_value(self, node):
        frame = np.zeros((100, 640, 3), dtype=np.uint8)
        result = node._preprocess(frame)
        # Padded areas should have value 114/255
        expected_pad_val = 114.0 / 255.0
        corner_val = result[0, 0, 0]
        assert corner_val == pytest.approx(expected_pad_val, abs=0.01)


class TestPostprocess:
    """Tests for the _postprocess method."""

    @pytest.fixture
    def node(self):
        obj = object.__new__(HailoInferenceNode)
        obj._input_width = 640
        obj._input_height = 640
        obj._confidence_threshold = 0.5
        obj._nms_threshold = 0.45
        obj._pad_info = (1.0, 0, 0)  # scale=1, no padding
        return obj

    def test_empty_output_returns_empty(self, node):
        result = node._postprocess({}, 640, 640)
        assert result == []

    def test_below_confidence_filtered(self, node):
        # Format: [cx, cy, w, h, class0_score]
        # Need num_rows >= num_cols to avoid transpose logic
        raw = np.array(
            [
                [0.5, 0.5, 0.1, 0.1, 0.3],
                [0.2, 0.2, 0.1, 0.1, 0.1],
                [0.3, 0.3, 0.1, 0.1, 0.1],
                [0.4, 0.4, 0.1, 0.1, 0.1],
                [0.6, 0.6, 0.1, 0.1, 0.1],
            ],
            dtype=np.float32,
        )
        result = node._postprocess({"output0": raw[np.newaxis, :]}, 640, 640)
        assert result == []

    def test_above_confidence_passes(self, node):
        raw = np.array(
            [
                [0.5, 0.5, 0.1, 0.1, 0.9],
                [0.2, 0.2, 0.1, 0.1, 0.1],
                [0.3, 0.3, 0.1, 0.1, 0.1],
                [0.4, 0.4, 0.1, 0.1, 0.1],
                [0.6, 0.6, 0.1, 0.1, 0.1],
            ],
            dtype=np.float32,
        )
        result = node._postprocess({"output0": raw[np.newaxis, :]}, 640, 640)
        assert len(result) == 1
        class_id, score, cx, cy, w, h = result[0]
        assert class_id == "0"
        assert score == pytest.approx(0.9)

    def test_multi_class_picks_highest(self, node):
        # 3 classes: scores [0.2, 0.8, 0.6] → picks class 1 with 0.8
        raw = np.array(
            [
                [0.5, 0.5, 0.1, 0.1, 0.2, 0.8, 0.6],
                [0.2, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.3, 0.3, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.4, 0.4, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.6, 0.6, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.7, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.8, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1],
            ],
            dtype=np.float32,
        )
        result = node._postprocess({"output0": raw[np.newaxis, :]}, 640, 640)
        assert len(result) == 1
        class_id, score, *_ = result[0]
        assert class_id == "1"
        assert score == pytest.approx(0.8)
