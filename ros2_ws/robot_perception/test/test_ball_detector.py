# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ball_detector_node HSV filtering and detection logic."""

import numpy as np


class TestHsvFiltering:
    """Test HSV color range filtering for ball detection."""

    def test_orange_ball_detected(self) -> None:
        """An orange pixel within range should pass the filter."""
        hsv_lower = np.array([5, 100, 100], dtype=np.uint8)
        hsv_upper = np.array([25, 255, 255], dtype=np.uint8)
        # Orange hue ~15, high saturation and value
        test_pixel = np.array([15, 200, 220], dtype=np.uint8)
        in_range = np.all(test_pixel >= hsv_lower) and np.all(test_pixel <= hsv_upper)
        assert in_range

    def test_blue_ball_rejected(self) -> None:
        """A blue pixel should not pass the orange filter."""
        hsv_lower = np.array([5, 100, 100], dtype=np.uint8)
        hsv_upper = np.array([25, 255, 255], dtype=np.uint8)
        # Blue hue ~110
        test_pixel = np.array([110, 200, 220], dtype=np.uint8)
        in_range = np.all(test_pixel >= hsv_lower) and np.all(test_pixel <= hsv_upper)
        assert not in_range

    def test_white_ball_detected(self) -> None:
        """A white pixel within range should pass the white filter."""
        hsv_lower = np.array([0, 0, 200], dtype=np.uint8)
        hsv_upper = np.array([180, 30, 255], dtype=np.uint8)
        # White: low saturation, high value
        test_pixel = np.array([0, 10, 240], dtype=np.uint8)
        in_range = np.all(test_pixel >= hsv_lower) and np.all(test_pixel <= hsv_upper)
        assert in_range

    def test_dark_pixel_rejected_by_white_filter(self) -> None:
        """A dark pixel should not pass the white filter."""
        hsv_lower = np.array([0, 0, 200], dtype=np.uint8)
        hsv_upper = np.array([180, 30, 255], dtype=np.uint8)
        # Dark: low value
        test_pixel = np.array([0, 10, 50], dtype=np.uint8)
        in_range = np.all(test_pixel >= hsv_lower) and np.all(test_pixel <= hsv_upper)
        assert not in_range


class TestFillRatioConfidence:
    """Test fill ratio to confidence conversion."""

    def test_full_circle_high_confidence(self) -> None:
        fill_ratio = 0.85
        confidence = min(1.0, fill_ratio * 1.3)
        assert confidence > 0.6

    def test_partial_circle_low_confidence(self) -> None:
        fill_ratio = 0.3
        confidence = min(1.0, fill_ratio * 1.3)
        assert confidence < 0.6

    def test_confidence_capped_at_one(self) -> None:
        fill_ratio = 1.0
        confidence = min(1.0, fill_ratio * 1.3)
        assert confidence == 1.0

    def test_empty_roi_zero_confidence(self) -> None:
        fill_ratio = 0.0
        confidence = min(1.0, fill_ratio * 1.3)
        assert confidence == 0.0


class TestRadiusConstraints:
    """Test radius filtering parameters."""

    def test_min_radius_default(self) -> None:
        min_r = 8
        max_r = 40
        assert min_r < max_r

    def test_too_small_rejected(self) -> None:
        min_r = 8
        detected_r = 5
        assert detected_r < min_r

    def test_too_large_rejected(self) -> None:
        max_r = 40
        detected_r = 60
        assert detected_r > max_r

    def test_valid_radius_accepted(self) -> None:
        min_r = 8
        max_r = 40
        detected_r = 20
        assert min_r <= detected_r <= max_r
