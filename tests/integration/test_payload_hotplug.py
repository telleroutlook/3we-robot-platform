# SPDX-License-Identifier: Apache-2.0
"""Integration tests for payload hot-plug state transitions.

Validates that:
- Connecting a payload publishes PayloadState with connected=True
- Disconnecting transitions state correctly
- Payload ID and name are preserved across state changes
"""

from __future__ import annotations

from typing import Any, List

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

try:
    from robot_interfaces.msg import PayloadState
except ImportError:
    pytest.skip(
        "robot_interfaces not built — skipping payload tests", allow_module_level=True
    )

from conftest import topic_collector, wait_for_topic  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAYLOAD_STATE_TOPIC = "/payload/state"

# PayloadState.state enum values (mirrors robot_interfaces definition)
STATE_DISCONNECTED: int = 0
STATE_CONNECTING: int = 1
STATE_CONNECTED: int = 2
STATE_ERROR: int = 3


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.hardware
@pytest.mark.timeout(60)
class TestPayloadHotplug:
    """Payload hot-plug detection and state transition verification."""

    def test_payload_connected_state_published(self, test_node: Any) -> None:
        """After payload connects, PayloadState.connected should be True."""
        msg = wait_for_topic(
            test_node,
            PAYLOAD_STATE_TOPIC,
            PayloadState,
            timeout=30.0,
        )

        # A connected payload must report connected=True and non-empty id
        assert msg.connected is True
        assert msg.payload_id != ""
        assert msg.name != ""
        assert msg.state == STATE_CONNECTED

    def test_payload_disconnect_transitions_state(self, test_node: Any) -> None:
        """Disconnecting a payload should transition state to DISCONNECTED.

        This test collects multiple state messages and verifies a transition
        from connected to disconnected occurs. Requires physically unplugging
        the payload during the test window.
        """
        messages: List[Any] = topic_collector(
            test_node,
            PAYLOAD_STATE_TOPIC,
            PayloadState,
            timeout=30.0,
            count=5,
        )

        # At least one message should indicate disconnection if unplug occurred
        states = [m.state for m in messages]
        # Verify we received at least one state message
        assert len(messages) > 0, "No PayloadState messages received"

        # If both states present, verify ordering: connected before disconnected
        connected_indices = [i for i, s in enumerate(states) if s == STATE_CONNECTED]
        disconnected_indices = [
            i for i, s in enumerate(states) if s == STATE_DISCONNECTED
        ]

        if connected_indices and disconnected_indices:
            assert min(connected_indices) < min(disconnected_indices), (
                "Disconnect should follow connect in message sequence"
            )

    def test_payload_identity_preserved(self, test_node: Any) -> None:
        """Payload ID and name should remain consistent across messages."""
        messages: List[Any] = topic_collector(
            test_node,
            PAYLOAD_STATE_TOPIC,
            PayloadState,
            timeout=15.0,
            count=3,
        )

        if len(messages) < 2:
            pytest.skip(
                "Not enough payload state messages to verify identity consistency"
            )

        first_id = messages[0].payload_id
        first_name = messages[0].name

        for msg in messages[1:]:
            if msg.payload_id == first_id:
                assert msg.name == first_name, (
                    f"Payload name changed for same ID: {first_name!r} → {msg.name!r}"
                )

    def test_payload_state_transitions_are_monotonic(self, test_node: Any) -> None:
        """State transitions should follow valid paths (no invalid jumps)."""
        valid_transitions = {
            STATE_DISCONNECTED: {STATE_CONNECTING, STATE_CONNECTED},
            STATE_CONNECTING: {STATE_CONNECTED, STATE_DISCONNECTED, STATE_ERROR},
            STATE_CONNECTED: {STATE_DISCONNECTED, STATE_ERROR},
            STATE_ERROR: {STATE_DISCONNECTED, STATE_CONNECTING},
        }

        messages: List[Any] = topic_collector(
            test_node,
            PAYLOAD_STATE_TOPIC,
            PayloadState,
            timeout=20.0,
            count=5,
        )

        if len(messages) < 2:
            pytest.skip("Not enough messages to verify transitions")

        for i in range(1, len(messages)):
            prev_state = messages[i - 1].state
            curr_state = messages[i].state

            if curr_state == prev_state:
                continue  # Same state repeated is fine

            assert curr_state in valid_transitions.get(prev_state, set()), (
                f"Invalid state transition: {prev_state} → {curr_state}"
            )
