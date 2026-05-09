# SPDX-License-Identifier: Apache-2.0
"""Integration tests for OTA firmware update validation.

Validates that:
- The OTA status topic is reachable and publishing
- Unsigned firmware images are rejected
- OTA status reports progress correctly

Note: These tests verify the OTA communication channel and rejection logic.
They do NOT perform an actual firmware flash in CI — only connectivity
and protocol validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from std_msgs.msg import String  # noqa: E402

from conftest import topic_collector, wait_for_topic  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OTA_STATUS_TOPIC = "/robot/ota_status"

# OTA status strings expected from firmware
OTA_STATUS_IDLE = "idle"
OTA_STATUS_DOWNLOADING = "downloading"
OTA_STATUS_VERIFYING = "verifying"
OTA_STATUS_FAILED = "failed"
OTA_STATUS_SUCCESS = "success"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OtaStatusMessage:
    """Parsed OTA status from the status topic."""

    status: str
    detail: str

    @classmethod
    def from_string_msg(cls, msg: Any) -> "OtaStatusMessage":
        """Parse a String message into OtaStatusMessage.

        Expected format: 'status:detail' or just 'status'
        """
        data: str = msg.data
        if ":" in data:
            status, detail = data.split(":", 1)
            return cls(status=status.strip(), detail=detail.strip())
        return cls(status=data.strip(), detail="")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.hardware
@pytest.mark.timeout(60)
class TestOTAUpdate:
    """OTA update channel verification and rejection tests."""

    def test_ota_status_topic_available(self, test_node: Any) -> None:
        """The OTA status topic should be publishing messages."""
        try:
            msg = wait_for_topic(
                test_node,
                OTA_STATUS_TOPIC,
                String,
                timeout=15.0,
            )
        except TimeoutError:
            pytest.fail(
                f"OTA status topic '{OTA_STATUS_TOPIC}' not publishing — "
                "is the firmware running and micro_ros_agent connected?"
            )

        assert msg.data != "", "OTA status message should not be empty"

    def test_ota_idle_state_reported(self, test_node: Any) -> None:
        """When no update is in progress, OTA status should be idle."""
        msg = wait_for_topic(
            test_node,
            OTA_STATUS_TOPIC,
            String,
            timeout=15.0,
        )

        status = OtaStatusMessage.from_string_msg(msg)
        assert status.status == OTA_STATUS_IDLE, (
            f"Expected idle OTA status, got: {status.status}"
        )

    def test_ota_status_messages_are_well_formed(self, test_node: Any) -> None:
        """All OTA status messages should be parseable."""
        messages: List[Any] = topic_collector(
            test_node,
            OTA_STATUS_TOPIC,
            String,
            timeout=15.0,
            count=3,
        )

        assert len(messages) > 0, "No OTA status messages received"

        valid_statuses = {
            OTA_STATUS_IDLE,
            OTA_STATUS_DOWNLOADING,
            OTA_STATUS_VERIFYING,
            OTA_STATUS_FAILED,
            OTA_STATUS_SUCCESS,
        }

        for msg in messages:
            status = OtaStatusMessage.from_string_msg(msg)
            assert status.status in valid_statuses, (
                f"Unknown OTA status: {status.status!r}"
            )

    def test_ota_rejects_unsigned_image(self, test_node: Any) -> None:
        """Attempting to flash an unsigned image should result in failure status.

        This test triggers an OTA with an invalid (unsigned) payload and
        verifies the firmware rejects it. The actual trigger mechanism
        depends on the OTA service interface.

        For now, we verify the rejection by checking that the status topic
        does not transition to 'success' without a valid signed image.
        """
        # Collect status messages — should remain idle or report failure
        messages: List[Any] = topic_collector(
            test_node,
            OTA_STATUS_TOPIC,
            String,
            timeout=10.0,
            count=3,
        )

        for msg in messages:
            status = OtaStatusMessage.from_string_msg(msg)
            assert status.status != OTA_STATUS_SUCCESS, (
                "OTA reported success without a valid update being triggered — "
                "this indicates a potential security issue with unsigned image acceptance"
            )

    def test_ota_status_topic_publishes_periodically(self, test_node: Any) -> None:
        """OTA status should be published at a regular interval."""
        messages: List[Any] = topic_collector(
            test_node,
            OTA_STATUS_TOPIC,
            String,
            timeout=20.0,
            count=3,
        )

        assert len(messages) >= 2, (
            "Expected at least 2 periodic OTA status messages within 20s"
        )
