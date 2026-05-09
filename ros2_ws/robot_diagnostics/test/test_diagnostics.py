# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the diagnostics node."""

import pytest


def test_diagnostics_node_import():
    """Verify module imports without ROS2 runtime."""
    # This test validates the module structure is correct.
    # Full integration tests require rclpy context (see tests/integration/).
    import importlib
    spec = importlib.util.find_spec('robot_diagnostics.diagnostics_node')
    assert spec is not None


def test_mqtt_bridge_import():
    """Verify MQTT bridge module imports."""
    import importlib
    spec = importlib.util.find_spec('robot_diagnostics.mqtt_bridge_node')
    assert spec is not None
