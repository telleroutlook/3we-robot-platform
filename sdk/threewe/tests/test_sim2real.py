# SPDX-License-Identifier: Apache-2.0
"""Tests for the Sim2Real validation protocol."""

from __future__ import annotations

import pytest

from threewe.benchmark.sim2real import (
    STANDARD_TRANSFER_TESTS,
    Sim2RealReport,
    Sim2RealTest,
    Sim2RealValidator,
    TransferMetric,
    TransferResult,
    evaluate_transfer,
)


class TestStandardTransferTests:
    def test_has_five_tests(self):
        assert len(STANDARD_TRANSFER_TESTS) == 5

    def test_all_have_names(self):
        names = [t.name for t in STANDARD_TRANSFER_TESTS]
        assert "straight_walk_5m" in names
        assert "rotation_360" in names
        assert "obstacle_avoidance_3" in names
        assert "pointnav_10m" in names
        assert "dynamic_obstacle" in names

    def test_all_are_frozen(self):
        test = STANDARD_TRANSFER_TESTS[0]
        with pytest.raises(AttributeError):
            test.name = "modified"  # type: ignore[misc]


class TestEvaluateTransfer:
    def test_real_lt_sim_times_mult_pass(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.ENDPOINT_ERROR,
            pass_multiplier=2.0,
            comparison="real_lt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.1, real_value=0.15)
        assert result.passed is True
        assert "PASS" in result.reason

    def test_real_lt_sim_times_mult_fail(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.ENDPOINT_ERROR,
            pass_multiplier=2.0,
            comparison="real_lt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.1, real_value=0.25)
        assert result.passed is False
        assert "FAIL" in result.reason

    def test_real_gt_sim_times_mult_pass(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.SUCCESS_RATE,
            pass_multiplier=0.7,
            comparison="real_gt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.9, real_value=0.8)
        assert result.passed is True

    def test_real_gt_sim_times_mult_fail(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.SUCCESS_RATE,
            pass_multiplier=0.7,
            comparison="real_gt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.9, real_value=0.5)
        assert result.passed is False

    def test_real_lt_absolute_pass(self):
        test = Sim2RealTest(
            name="rotation",
            description="test",
            metric=TransferMetric.ANGLE_ERROR,
            pass_multiplier=5.0,
            comparison="real_lt_absolute",
        )
        result = evaluate_transfer(test, sim_value=2.0, real_value=3.0)
        assert result.passed is True

    def test_real_lt_absolute_fail(self):
        test = Sim2RealTest(
            name="rotation",
            description="test",
            metric=TransferMetric.ANGLE_ERROR,
            pass_multiplier=5.0,
            comparison="real_lt_absolute",
        )
        result = evaluate_transfer(test, sim_value=2.0, real_value=6.0)
        assert result.passed is False

    def test_transfer_ratio_computed(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.ENDPOINT_ERROR,
            pass_multiplier=2.0,
            comparison="real_lt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.1, real_value=0.15)
        assert result.transfer_ratio == pytest.approx(1.5)

    def test_zero_sim_value(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.ENDPOINT_ERROR,
            pass_multiplier=2.0,
            comparison="real_lt_sim_times_mult",
        )
        result = evaluate_transfer(test, sim_value=0.0, real_value=0.0)
        assert result.transfer_ratio == 1.0
        assert result.passed is True

    def test_unknown_comparison(self):
        test = Sim2RealTest(
            name="test",
            description="test",
            metric=TransferMetric.ENDPOINT_ERROR,
            pass_multiplier=2.0,
            comparison="unknown_type",
        )
        result = evaluate_transfer(test, sim_value=0.1, real_value=0.05)
        assert result.passed is False
        assert "Unknown" in result.reason


class TestSim2RealReport:
    def test_report_construction(self):
        results = (
            TransferResult("a", 0.1, 0.15, 1.5, True, "PASS"),
            TransferResult("b", 0.9, 0.5, 0.56, False, "FAIL"),
        )
        report = Sim2RealReport(
            results=results,
            overall_passed=False,
            pass_rate=0.5,
            timestamp="2025-01-01T00:00:00",
        )
        assert len(report.results) == 2
        assert report.pass_rate == 0.5
        assert report.overall_passed is False

    def test_report_is_frozen(self):
        report = Sim2RealReport(results=(), overall_passed=True, pass_rate=1.0, timestamp="")
        with pytest.raises(AttributeError):
            report.pass_rate = 0.0  # type: ignore[misc]


class TestSim2RealValidator:
    def test_default_tests(self):
        validator = Sim2RealValidator()
        assert len(validator.tests) == 5

    def test_custom_tests(self):
        custom = [STANDARD_TRANSFER_TESTS[0]]
        validator = Sim2RealValidator(tests=custom)
        assert len(validator.tests) == 1
