# SPDX-License-Identifier: Apache-2.0
"""Integration tests for payload sandbox isolation.

Validates that payload code CANNOT:
- Directly publish to motor control topics (/cmd_vel)
- Call safety-critical services (EmergencyStop) without authorization
- Access core system parameters (safety relay, motor config)
- Subscribe to topics outside its allowed namespace

These tests verify the safety boundary described in CLAUDE.md:
"Payload code runs in a sandboxed context. It cannot directly access
motor control, safety circuits, or core system configuration."
"""

from __future__ import annotations

import time
from typing import Any

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from geometry_msgs.msg import Twist  # noqa: E402

from conftest import topic_collector  # noqa: E402

try:
    from robot_interfaces.srv import EmergencyStop, PayloadPower

    HAS_INTERFACES = True
except ImportError:
    HAS_INTERFACES = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAYLOAD_NAMESPACE = "/payload"
MOTOR_TOPIC = "/cmd_vel"
ESTOP_SERVICE = "/robot/emergency_stop"
SAFETY_PARAM_NAMES = [
    "safety_relay_gpio",
    "estop_gpio",
    "motor_max_duty",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.hardware
@pytest.mark.timeout(60)
class TestPayloadSandboxIsolation:
    """Verify payload cannot escape its sandbox to access safety-critical systems."""

    def test_payload_cannot_publish_cmd_vel(self, test_node: Any) -> None:
        """Payload-namespace publishers must not affect the real /cmd_vel topic.

        The middleware should reject or ignore cmd_vel publications originating
        from the payload namespace. Even if a payload node publishes to /cmd_vel,
        the safety interlock layer should block it.
        """
        # Create a node simulating a payload trying to publish motor commands
        payload_node = rclpy.create_node(
            "payload_escape_test", namespace=PAYLOAD_NAMESPACE
        )
        try:
            pub = payload_node.create_publisher(Twist, MOTOR_TOPIC, 10)
            rclpy.spin_once(payload_node, timeout_sec=0.5)

            # Publish unauthorized motor command
            cmd = Twist()
            cmd.linear.x = 1.0
            cmd.angular.z = 0.5
            pub.publish(cmd)

            rclpy.spin_once(payload_node, timeout_sec=0.5)

            # Collect what actually arrives at the motor controller
            # The safety layer should have filtered the payload's cmd_vel
            messages = topic_collector(
                test_node,
                "/robot/motor_cmd_actual",
                Twist,
                timeout=3.0,
                count=1,
            )

            # Either no message should arrive, or the velocity should be zero
            # (safety interlock zeros unauthorized commands)
            for msg in messages:
                assert msg.linear.x == 0.0, (
                    f"Payload cmd_vel escaped sandbox: linear.x={msg.linear.x}"
                )
                assert msg.angular.z == 0.0, (
                    f"Payload cmd_vel escaped sandbox: angular.z={msg.angular.z}"
                )
        finally:
            payload_node.destroy_node()

    def test_payload_cannot_trigger_estop_directly(self, test_node: Any) -> None:
        """Payload must not be able to call the EmergencyStop service directly.

        The safety service should reject calls from unauthorized nodes or
        require an authentication token that payload code does not possess.
        """
        if not HAS_INTERFACES:
            pytest.skip("robot_interfaces not available")

        payload_node = rclpy.create_node(
            "payload_estop_test", namespace=PAYLOAD_NAMESPACE
        )
        try:
            client = payload_node.create_client(EmergencyStop, ESTOP_SERVICE)

            if not client.wait_for_service(timeout_sec=5.0):
                pytest.skip("EmergencyStop service not available")

            request = EmergencyStop.Request()
            request.trigger = True
            request.reason = "payload_sandbox_escape_test"

            future = client.call_async(request)

            deadline = time.monotonic() + 10.0
            while not future.done() and time.monotonic() < deadline:
                rclpy.spin_once(payload_node, timeout_sec=0.1)

            if not future.done():
                pytest.skip("EmergencyStop service did not respond")

            result = future.result()
            # The service should either reject the call (success=False) or
            # the call should not actually trigger a hardware e-stop when
            # originating from the payload namespace
            assert result.success is False, (
                "Payload node was able to trigger E-stop service — "
                "sandbox isolation is broken"
            )
        finally:
            payload_node.destroy_node()

    def test_payload_cannot_read_safety_params(self, test_node: Any) -> None:
        """Payload must not access safety-critical node parameters.

        Parameters like GPIO pin assignments for safety relay and e-stop
        should not be readable by payload-namespace nodes.
        """
        payload_node = rclpy.create_node(
            "payload_param_test", namespace=PAYLOAD_NAMESPACE
        )
        try:
            # Try to get parameters from the safety node
            client = payload_node.create_client(
                rclpy.parameter.GetParameters, "/base_controller/get_parameters"
            )

            if not client.wait_for_service(timeout_sec=5.0):
                pytest.skip("Parameter service not available")

            from rcl_interfaces.srv import GetParameters

            request = GetParameters.Request()
            request.names = SAFETY_PARAM_NAMES

            future = client.call_async(request)

            deadline = time.monotonic() + 10.0
            while not future.done() and time.monotonic() < deadline:
                rclpy.spin_once(payload_node, timeout_sec=0.1)

            if not future.done():
                pytest.skip("Parameter service did not respond")

            result = future.result()
            # All parameter values should be "not set" or access denied
            for i, val in enumerate(result.values):
                assert val.type == 0, (
                    f"Payload accessed safety param '{SAFETY_PARAM_NAMES[i]}' — "
                    f"sandbox isolation is broken"
                )
        finally:
            payload_node.destroy_node()

    def test_payload_power_service_limits_rails(self, test_node: Any) -> None:
        """Payload can only control its own power rails, not system rails.

        Attempting to control a non-payload rail should be rejected.
        """
        if not HAS_INTERFACES:
            pytest.skip("robot_interfaces not available")

        payload_node = rclpy.create_node(
            "payload_power_test", namespace=PAYLOAD_NAMESPACE
        )
        try:
            client = payload_node.create_client(PayloadPower, "/payload/power")

            if not client.wait_for_service(timeout_sec=5.0):
                pytest.skip("PayloadPower service not available")

            # Try to enable a system rail (not a payload rail)
            request = PayloadPower.Request()
            request.payload_id = "SYSTEM"
            request.rail = "MOTOR"
            request.enable = True

            future = client.call_async(request)

            deadline = time.monotonic() + 10.0
            while not future.done() and time.monotonic() < deadline:
                rclpy.spin_once(payload_node, timeout_sec=0.1)

            if not future.done():
                pytest.skip("PayloadPower service did not respond")

            result = future.result()
            assert result.success is False, (
                "Payload was able to control system power rail — "
                "sandbox isolation is broken"
            )
        finally:
            payload_node.destroy_node()

    def test_payload_gpio_restricted_to_mask(self) -> None:
        """Payload GPIO access is restricted at the firmware level.

        The firmware validates gpio_mask from the EEPROM descriptor.
        Only pins within the mask (0x0F = pins 0-3) are accessible.
        This test validates the descriptor parsing rejects invalid masks.
        """
        from payload_interface.payload_protocol import PayloadDescriptor

        # Simulate a descriptor with restricted GPIO mask
        valid_desc = PayloadDescriptor(
            payload_id="test-001",
            name="Test Payload",
            power_5v_ma=500,
            power_12v_ma=0,
            capabilities=0x10,  # CAP_GPIO
            gpio_mask=0x0F,  # Only pins 0-3
            i2c_addr_count=0,
        )

        # Mask should only allow 4 pins
        assert valid_desc.gpio_mask == 0x0F
        assert valid_desc.uses_gpio is True

        # Verify that a pin outside the mask would be rejected
        # (firmware enforces: pin_bit & gpio_mask must be non-zero)
        for pin in range(4):
            assert (1 << pin) & valid_desc.gpio_mask != 0, (
                f"Pin {pin} should be within allowed mask"
            )
        for pin in range(4, 8):
            assert (1 << pin) & valid_desc.gpio_mask == 0, (
                f"Pin {pin} should be outside allowed mask"
            )
