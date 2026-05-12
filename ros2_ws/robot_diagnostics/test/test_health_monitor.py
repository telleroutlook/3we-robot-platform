# SPDX-License-Identifier: Apache-2.0
"""Unit tests for HealthMonitorNode evaluation functions."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self, *a, **kw):
        pass

    def declare_parameter(self, *a, **kw):
        pass

    def get_parameter(self, *a, **kw):
        return MagicMock(value=0)

    def create_publisher(self, *a, **kw):
        return MagicMock()

    def create_timer(self, *a, **kw):
        return MagicMock()

    def get_clock(self):
        return MagicMock()

    def get_logger(self):
        return MagicMock()


# Mock rclpy before importing
_rclpy_mock = MagicMock()
_node_mod = MagicMock()
_node_mod.Node = _FakeNode
sys.modules.setdefault("rclpy", _rclpy_mock)
sys.modules["rclpy.node"] = _node_mod
sys.modules.setdefault("rclpy.qos", MagicMock())
sys.modules.setdefault("std_msgs.msg", MagicMock())

# Mock diagnostic_msgs with real-enough constants
diag_mock = MagicMock()
diag_status_cls = type(
    "DiagnosticStatus",
    (),
    {"OK": 0, "WARN": 1, "ERROR": 2, "STALE": 3},
)
diag_mock.DiagnosticStatus = diag_status_cls
diag_mock.DiagnosticArray = MagicMock()
diag_mock.KeyValue = lambda key="", value="": SimpleNamespace(key=key, value=value)
sys.modules["diagnostic_msgs.msg"] = diag_mock

from robot_diagnostics.health_monitor_node import HealthMonitorNode, HealthThresholds  # noqa: E402


@pytest.fixture
def thresholds():
    return HealthThresholds(
        cpu_temp_warn=75.0,
        cpu_temp_critical=85.0,
        memory_warn_pct=85.0,
        memory_critical_pct=95.0,
        wifi_rssi_warn=-75,
        wifi_rssi_critical=-85,
        disk_warn_gb=2.0,
        disk_critical_gb=0.5,
    )


@pytest.fixture
def node(thresholds):
    obj = object.__new__(HealthMonitorNode)
    obj._thresholds = thresholds
    return obj


class TestEvaluateCpuTemp:
    def test_normal_temperature(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(50.0, penalties)
        assert status.level == 0  # OK
        assert penalties == []

    def test_warning_temperature(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(78.0, penalties)
        assert status.level == 1  # WARN
        assert penalties == [20.0]

    def test_critical_temperature(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(90.0, penalties)
        assert status.level == 2  # ERROR
        assert penalties == [50.0]

    def test_none_temperature(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(None, penalties)
        assert status.level == 3  # STALE
        assert penalties == []

    def test_at_warn_boundary(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(75.0, penalties)
        assert status.level == 1  # WARN

    def test_at_critical_boundary(self, node):
        penalties = []
        status = node._evaluate_cpu_temp(85.0, penalties)
        assert status.level == 2  # ERROR


class TestEvaluateMemory:
    def test_normal_usage(self, node):
        penalties = []
        status = node._evaluate_memory(60.0, penalties)
        assert status.level == 0
        assert penalties == []

    def test_warning_usage(self, node):
        penalties = []
        status = node._evaluate_memory(90.0, penalties)
        assert status.level == 1
        assert penalties == [15.0]

    def test_critical_usage(self, node):
        penalties = []
        status = node._evaluate_memory(97.0, penalties)
        assert status.level == 2
        assert penalties == [40.0]

    def test_none_usage(self, node):
        penalties = []
        status = node._evaluate_memory(None, penalties)
        assert status.level == 3


class TestEvaluateWifi:
    def test_good_signal(self, node):
        penalties = []
        status = node._evaluate_wifi(-50, penalties)
        assert status.level == 0
        assert penalties == []

    def test_warning_signal(self, node):
        penalties = []
        status = node._evaluate_wifi(-80, penalties)
        assert status.level == 1
        assert penalties == [15.0]

    def test_critical_signal(self, node):
        penalties = []
        status = node._evaluate_wifi(-90, penalties)
        assert status.level == 2
        assert penalties == [35.0]

    def test_disconnected(self, node):
        penalties = []
        status = node._evaluate_wifi(None, penalties)
        assert status.level == 3
        assert penalties == [30.0]

    def test_at_warn_boundary(self, node):
        penalties = []
        status = node._evaluate_wifi(-75, penalties)
        assert status.level == 1


class TestEvaluateDisk:
    def test_ample_space(self, node):
        penalties = []
        status = node._evaluate_disk(10.0, penalties)
        assert status.level == 0
        assert penalties == []

    def test_warning_space(self, node):
        penalties = []
        status = node._evaluate_disk(1.5, penalties)
        assert status.level == 1
        assert penalties == [10.0]

    def test_critical_space(self, node):
        penalties = []
        status = node._evaluate_disk(0.3, penalties)
        assert status.level == 2
        assert penalties == [30.0]

    def test_none_space(self, node):
        penalties = []
        status = node._evaluate_disk(None, penalties)
        assert status.level == 3

    def test_at_critical_boundary(self, node):
        penalties = []
        status = node._evaluate_disk(0.5, penalties)
        assert status.level == 2
