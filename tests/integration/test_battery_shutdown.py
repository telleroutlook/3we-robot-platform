# SPDX-License-Identifier: Apache-2.0
"""Integration tests for battery low shutdown sequence.

Validates that:
- BatteryState messages are published on /battery_state
- Low battery triggers graceful shutdown behavior
- Emergency stop is activated before power loss
- Battery percentage is within valid range
"""

from __future__ import annotations

from typing import Any, List

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from sensor_msgs.msg import BatteryState  # noqa: E402

try:
    from robot_interfaces.msg import EmergencyStopState
except ImportError:
    EmergencyStopState = None  # type: ignore[assignment, misc]

from conftest import topic_collector, wait_for_topic  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATTERY_TOPIC = "/battery_state"
ESTOP_STATE_TOPIC = "/emergency_stop_state"

# Battery thresholds (volts for 3S LiPo, typical)
BATTERY_CRITICAL_PERCENTAGE: float = 10.0  # Below this triggers shutdown
BATTERY_LOW_PERCENTAGE: float = 20.0  # Below this triggers warning
BATTERY_VALID_MIN_VOLTAGE: float = 9.0  # 3S LiPo minimum
BATTERY_VALID_MAX_VOLTAGE: float = 12.6  # 3S LiPo fully charged


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.hardware
@pytest.mark.timeout(60)
class TestBatteryShutdown:
    """Battery monitoring and graceful shutdown verification."""

    def test_battery_state_published(self, test_node: Any) -> None:
        """BatteryState messages should be published on /battery_state."""
        try:
            msg = wait_for_topic(
                test_node,
                BATTERY_TOPIC,
                BatteryState,
                timeout=15.0,
            )
        except TimeoutError:
            pytest.fail(
                f"Battery state topic '{BATTERY_TOPIC}' not publishing — "
                "is the battery monitor node running?"
            )

        # Basic validity checks
        assert msg.percentage >= 0.0, "Battery percentage should not be negative"
        assert 0.0 <= msg.percentage <= 1.0, (
            f"Battery percentage out of valid range [0, 1]: {msg.percentage}. "
            "sensor_msgs/BatteryState defines percentage as a value in [0, 1]."
        )

    def test_battery_voltage_within_valid_range(self, test_node: Any) -> None:
        """Reported battery voltage should be within physically valid range."""
        msg = wait_for_topic(
            test_node,
            BATTERY_TOPIC,
            BatteryState,
            timeout=15.0,
        )

        # voltage field may be 0 if not reported; skip in that case
        if msg.voltage == 0.0:
            pytest.skip("Battery voltage not reported (field is 0)")

        assert msg.voltage >= BATTERY_VALID_MIN_VOLTAGE, (
            f"Battery voltage {msg.voltage}V below minimum {BATTERY_VALID_MIN_VOLTAGE}V — "
            "battery may be critically low or sensor fault"
        )
        assert msg.voltage <= BATTERY_VALID_MAX_VOLTAGE, (
            f"Battery voltage {msg.voltage}V above maximum {BATTERY_VALID_MAX_VOLTAGE}V — "
            "sensor calibration issue"
        )

    def test_battery_percentage_consistency(self, test_node: Any) -> None:
        """Multiple battery readings should be consistent (no wild jumps)."""
        messages: List[Any] = topic_collector(
            test_node,
            BATTERY_TOPIC,
            BatteryState,
            timeout=15.0,
            count=5,
        )

        if len(messages) < 2:
            pytest.skip("Not enough battery messages to verify consistency")

        for i in range(1, len(messages)):
            prev = messages[i - 1].percentage
            curr = messages[i].percentage
            delta = abs(curr - prev)

            # Battery percentage should not jump more than 5% between readings
            # percentage is in [0.0, 1.0] per ROS2 BatteryState spec
            assert delta < 0.05, (
                f"Battery percentage jumped {delta * 100:.1f}% between consecutive readings "
                f"({prev * 100:.1f}% → {curr * 100:.1f}%) — possible sensor fault"
            )

    def test_low_battery_triggers_warning_state(self, test_node: Any) -> None:
        """If battery is below low threshold, system should indicate warning.

        This test checks the current battery level. If it happens to be
        below the warning threshold, it verifies the system has responded
        appropriately. If battery is healthy, the test passes trivially.
        """
        msg = wait_for_topic(
            test_node,
            BATTERY_TOPIC,
            BatteryState,
            timeout=15.0,
        )

        # Normalize percentage (some implementations use 0-1, others 0-100)
        percentage = msg.percentage
        if percentage <= 1.0:
            percentage = percentage * 100.0

        if percentage > BATTERY_LOW_PERCENTAGE:
            # Battery is healthy — nothing to verify about shutdown behavior
            return

        # Battery is low — verify power_supply_status indicates discharging
        # BatteryState.POWER_SUPPLY_STATUS_DISCHARGING = 2
        assert msg.power_supply_status == 2 or msg.power_supply_status == 3, (
            f"Low battery ({percentage:.1f}%) but status is not DISCHARGING or NOT_CHARGING"
        )

    def test_critical_battery_activates_estop(self, test_node: Any) -> None:
        """Critical battery level should activate emergency stop before shutdown.

        This verifies the safety design: when battery reaches critical level,
        the system must stop all motors before power is lost to prevent
        uncontrolled coasting.

        Note: This test only validates the relationship if battery is
        currently critical. It does not drain the battery intentionally.
        """
        if EmergencyStopState is None:
            pytest.skip("robot_interfaces not available for E-stop state check")

        battery_msg = wait_for_topic(
            test_node,
            BATTERY_TOPIC,
            BatteryState,
            timeout=15.0,
        )

        # Normalize percentage
        percentage = battery_msg.percentage
        if percentage <= 1.0:
            percentage = percentage * 100.0

        if percentage > BATTERY_CRITICAL_PERCENTAGE:
            # Battery is above critical — cannot verify shutdown behavior
            pytest.skip(
                f"Battery at {percentage:.1f}% (above critical threshold "
                f"{BATTERY_CRITICAL_PERCENTAGE}%) — cannot test shutdown activation"
            )

        # Battery IS critical — verify E-stop is activated
        estop_msg = wait_for_topic(
            test_node,
            ESTOP_STATE_TOPIC,
            EmergencyStopState,
            timeout=5.0,
        )

        assert estop_msg.stopped is True, (
            f"Battery critical ({percentage:.1f}%) but E-stop not activated — "
            "safety violation: motors must be stopped before battery cutoff"
        )

    def test_battery_publishes_periodically(self, test_node: Any) -> None:
        """Battery state should be published at regular intervals."""
        messages: List[Any] = topic_collector(
            test_node,
            BATTERY_TOPIC,
            BatteryState,
            timeout=15.0,
            count=3,
        )

        assert len(messages) >= 2, (
            "Expected at least 2 periodic battery messages within 15s"
        )
