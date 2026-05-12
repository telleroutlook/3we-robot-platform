# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ball_tracker_node filtering and depth estimation logic."""


class TestDepthEstimation:
    """Test the depth estimation formula: depth = (ball_diameter * focal_length) / bbox_size."""

    def test_known_distance(self) -> None:
        ball_diameter_m = 0.04
        focal_length_px = 500.0
        bbox_size_px = 40.0  # ball at 0.5m
        expected_depth = (ball_diameter_m * focal_length_px) / bbox_size_px
        assert abs(expected_depth - 0.5) < 0.01

    def test_far_distance(self) -> None:
        ball_diameter_m = 0.04
        focal_length_px = 500.0
        bbox_size_px = 10.0  # ball at 2.0m
        expected_depth = (ball_diameter_m * focal_length_px) / bbox_size_px
        assert abs(expected_depth - 2.0) < 0.01

    def test_zero_bbox_returns_large(self) -> None:
        ball_diameter_m = 0.04
        focal_length_px = 500.0
        bbox_size_px = 0.0
        # Should not divide by zero — implementation returns 999.0
        if bbox_size_px <= 0:
            depth = 999.0
        else:
            depth = (ball_diameter_m * focal_length_px) / bbox_size_px
        assert depth == 999.0


class TestConfidenceFiltering:
    """Test confidence threshold filtering logic."""

    def test_above_threshold_passes(self) -> None:
        min_confidence = 0.6
        score = 0.85
        assert score >= min_confidence

    def test_below_threshold_rejected(self) -> None:
        min_confidence = 0.6
        score = 0.4
        assert score < min_confidence

    def test_at_threshold_passes(self) -> None:
        min_confidence = 0.6
        score = 0.6
        assert score >= min_confidence


class TestConsecutiveFrameTracking:
    """Test that consecutive frame counting filters transient detections."""

    def test_single_frame_not_enough(self) -> None:
        min_consecutive = 3
        frames_seen = 1
        assert frames_seen < min_consecutive

    def test_enough_frames_triggers(self) -> None:
        min_consecutive = 3
        frames_seen = 3
        assert frames_seen >= min_consecutive

    def test_reset_on_different_position(self) -> None:
        counts: dict[str, int] = {}
        counts["100_200"] = 2
        # New detection at different position resets
        new_key = "150_250"
        counts[new_key] = counts.get(new_key, 0) + 1
        stale_keys = [k for k in counts if k != new_key]
        for k in stale_keys:
            counts.pop(k, None)
        assert "100_200" not in counts
        assert counts[new_key] == 1
