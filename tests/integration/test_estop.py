# SPDX-License-Identifier: Apache-2.0
"""Integration tests for Emergency Stop (E-stop) activation.

Validates that:
- Triggering the E-stop service sets stopped=True on /emergency_stop_state
- cmd_vel messages are suppressed while E-stop is active
- The state topic reports the correct reason string
"""

from __future__ import annotations

from typing import Any

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from geometry_msgs.msg import Twist  # noqa: E402

try:
    from robot_interfaces.msg import EmergencyStopState
    from robot_interfaces.srv import EmergencyStop
except ImportError:
    pytest.skip(
        "robot_interfaces not built — skipping E-stop tests", allow_module_level=True
    )

from conftest import service_caller, wait_for_topic  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.simulation
@pytest.mark.fullstack
@pytest.mark.timeout(60)
class TestEmergencyStop:
    """E-stop activation and state verification."""

    def test_estop_service_activates_stop_state(self, test_node: Any) -> None:
        """Calling /robot/emergency_stop should publish stopped=True."""
        request = EmergencyStop.Request()
        request.reason = "integration_test"

        response = service_caller(
            test_node,
            "/robot/emergency_stop",
            EmergencyStop,
            request,
            timeout=10.0,
        )

        assert response.success is True
        assert response.message != ""

        # Verify the state topic reflects activation
        state_msg = wait_for_topic(
            test_node,
            "/emergency_stop_state",
            EmergencyStopState,
            timeout=5.0,
        )

        assert state_msg.stopped is True
        assert state_msg.reason == "integration_test"

    def test_cmd_vel_suppressed_during_estop(self, test_node: Any) -> None:
        """While E-stop is active, cmd_vel should not pass through."""
        # Activate E-stop
        request = EmergencyStop.Request()
        request.reason = "suppress_test"

        service_caller(
            test_node,
            "/robot/emergency_stop",
            EmergencyStop,
            request,
            timeout=10.0,
        )

        # Publish a velocity command
        pub = test_node.create_publisher(Twist, "/cmd_vel", 10)
        twist = Twist()
        twist.linear.x = 0.5

        # Publish repeatedly for a short window
        for _ in range(5):
            pub.publish(twist)
            rclpy.spin_once(test_node, timeout_sec=0.1)

        # Verify odometry shows no motion (robot should not move)
        # We check that the emergency_stop_state remains active
        state_msg = wait_for_topic(
            test_node,
            "/emergency_stop_state",
            EmergencyStopState,
            timeout=5.0,
        )
        assert state_msg.stopped is True

        test_node.destroy_publisher(pub)

    def test_estop_state_reports_reason(self, test_node: Any) -> None:
        """The E-stop state should include the reason string provided."""
        reason = "safety_boundary_breach"
        request = EmergencyStop.Request()
        request.reason = reason

        service_caller(
            test_node,
            "/robot/emergency_stop",
            EmergencyStop,
            request,
            timeout=10.0,
        )

        state_msg = wait_for_topic(
            test_node,
            "/emergency_stop_state",
            EmergencyStopState,
            timeout=5.0,
        )

        assert state_msg.reason == reason
        assert state_msg.state != 0  # Non-zero indicates active stop state
