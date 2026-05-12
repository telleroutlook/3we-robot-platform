# SPDX-License-Identifier: Apache-2.0
"""Unit tests for NotificationDispatcher pure logic methods."""

import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class _FakeNode:
    def __init__(self, *a, **kw):
        pass

    def declare_parameter(self, *a, **kw):
        pass

    def get_parameter(self, *a, **kw):
        return MagicMock(get_parameter_value=lambda: MagicMock(string_value=""))

    def create_subscription(self, *a, **kw):
        return MagicMock()

    def get_logger(self):
        return MagicMock()


# Mock rclpy and yaml before importing
_rclpy_mock = MagicMock()
_node_mod = MagicMock()
_node_mod.Node = _FakeNode
sys.modules.setdefault("rclpy", _rclpy_mock)
sys.modules["rclpy.node"] = _node_mod
sys.modules.setdefault("yaml", MagicMock())

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

from robot_diagnostics.notification_dispatcher import NotificationDispatcher  # noqa: E402


@pytest.fixture
def dispatcher():
    obj = object.__new__(NotificationDispatcher)
    obj._config = {
        "channels": [],
        "throttling": {"duplicate_window_seconds": 60, "quiet_hours": {}},
        "templates": {},
    }
    obj._recent_events = {}
    return obj


class TestLevelToSeverity:
    def test_error_maps_to_critical(self, dispatcher):
        assert dispatcher._level_to_severity(2) == "critical"

    def test_warn_maps_to_warning(self, dispatcher):
        assert dispatcher._level_to_severity(1) == "warning"

    def test_ok_maps_to_none(self, dispatcher):
        assert dispatcher._level_to_severity(0) is None

    def test_stale_maps_to_none(self, dispatcher):
        assert dispatcher._level_to_severity(3) is None


class TestShouldDispatch:
    def test_first_event_dispatches(self, dispatcher):
        event = {"event_type": "CPU Temperature", "severity": "critical"}
        assert dispatcher._should_dispatch(event) is True

    def test_duplicate_within_window_blocked(self, dispatcher):
        event = {"event_type": "CPU Temperature", "severity": "critical"}
        dispatcher._recent_events["CPU Temperature:critical"] = time.time()
        assert dispatcher._should_dispatch(event) is False

    def test_duplicate_after_window_dispatches(self, dispatcher):
        event = {"event_type": "CPU Temperature", "severity": "critical"}
        dispatcher._recent_events["CPU Temperature:critical"] = time.time() - 120
        assert dispatcher._should_dispatch(event) is True

    def test_different_event_types_independent(self, dispatcher):
        event1 = {"event_type": "CPU Temperature", "severity": "critical"}
        event2 = {"event_type": "Memory Usage", "severity": "critical"}
        dispatcher._should_dispatch(event1)
        assert dispatcher._should_dispatch(event2) is True

    def test_quiet_hours_blocks_warning(self, dispatcher):
        dispatcher._config["throttling"]["quiet_hours"] = {
            "start": "22:00",
            "end": "08:00",
            "allowed_levels": ["critical"],
        }
        event = {"event_type": "Disk Space", "severity": "warning"}
        # Simulate being in quiet hours (23:00)
        with patch(
            "robot_diagnostics.notification_dispatcher.datetime"
        ) as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 23
            mock_datetime.now.return_value = mock_now
            result = dispatcher._should_dispatch(event)
        assert result is False

    def test_quiet_hours_allows_critical(self, dispatcher):
        dispatcher._config["throttling"]["quiet_hours"] = {
            "start": "22:00",
            "end": "08:00",
            "allowed_levels": ["critical"],
        }
        event = {"event_type": "CPU Temperature", "severity": "critical"}
        with patch(
            "robot_diagnostics.notification_dispatcher.datetime"
        ) as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 23
            mock_datetime.now.return_value = mock_now
            result = dispatcher._should_dispatch(event)
        assert result is True


class TestFormatForChannel:
    @pytest.fixture
    def dispatcher_with_templates(self, dispatcher):
        dispatcher._config["templates"] = {
            "default": {
                "title": "[{severity}] {event_type}",
                "body": "{details}",
            }
        }
        return dispatcher

    def test_slack_format(self, dispatcher_with_templates):
        event = {
            "robot_id": "robot-001",
            "event_type": "CPU Temperature",
            "severity": "critical",
            "timestamp": "2026-05-12T10:00:00",
            "details": "CRITICAL: 90.5°C",
            "battery_percent": "85",
        }
        channel = {"type": "slack", "template": "default"}
        result = dispatcher_with_templates._format_for_channel(event, channel)
        assert "blocks" in result
        assert len(result["blocks"]) > 0

    def test_dingtalk_format(self, dispatcher_with_templates):
        event = {
            "robot_id": "robot-001",
            "event_type": "CPU Temperature",
            "severity": "warning",
            "timestamp": "2026-05-12T10:00:00",
            "details": "Warning: 78.0°C",
            "battery_percent": "85",
        }
        channel = {"type": "dingtalk", "template": "default"}
        result = dispatcher_with_templates._format_for_channel(event, channel)
        assert result["msgtype"] == "actionCard"
        assert "actionCard" in result

    def test_feishu_format(self, dispatcher_with_templates):
        event = {
            "robot_id": "robot-001",
            "event_type": "Memory Usage",
            "severity": "critical",
            "timestamp": "2026-05-12T10:00:00",
            "details": "CRITICAL: 97.0%",
            "battery_percent": "85",
        }
        channel = {"type": "feishu", "template": "default"}
        result = dispatcher_with_templates._format_for_channel(event, channel)
        assert result["msg_type"] == "interactive"
        assert "card" in result
        assert result["card"]["header"]["template"] == "red"

    def test_generic_webhook_format(self, dispatcher_with_templates):
        event = {
            "robot_id": "robot-001",
            "event_type": "Disk Space",
            "severity": "warning",
            "timestamp": "2026-05-12T10:00:00",
            "details": "Warning: 1.5 GB free",
            "battery_percent": "85",
        }
        channel = {"type": "webhook", "template": "default"}
        result = dispatcher_with_templates._format_for_channel(event, channel)
        assert "title" in result
        assert "[warning] Disk Space" in result["title"]


class TestFormatPayload:
    def test_template_substitution(self, dispatcher):
        dispatcher._config["templates"] = {
            "custom": {
                "title": "ALERT: {event_type} on {robot_id}",
                "body": "{details} (battery: {battery_percent}%)",
            }
        }
        event = {
            "robot_id": "bot-42",
            "event_type": "Overheating",
            "severity": "critical",
            "timestamp": "2026-05-12T10:00:00",
            "details": "CPU at 95C",
            "battery_percent": "42",
        }
        result = dispatcher._format_payload(event, "custom")
        assert result["title"] == "ALERT: Overheating on bot-42"
        assert "CPU at 95C" in result["body"]
        assert "42%" in result["body"]

    def test_missing_template_uses_defaults(self, dispatcher):
        dispatcher._config["templates"] = {}
        event = {
            "robot_id": "robot-001",
            "event_type": "Test",
            "severity": "warning",
            "timestamp": "2026-05-12T10:00:00",
            "details": "some detail",
            "battery_percent": "N/A",
        }
        result = dispatcher._format_payload(event, "nonexistent")
        assert "[warning] Test" in result["title"]
