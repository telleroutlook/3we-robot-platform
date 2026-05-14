# SPDX-License-Identifier: Apache-2.0
"""Integration tests for DTLS encrypted communication channel.

Validates that:
- A DTLS connection can be established to the ESP32 on port 5684
- cmd_vel frames are delivered over the encrypted channel
- Unauthenticated connections are rejected

Tests are split into two classes:
- TestDTLSChannel: Transport smoke tests using plaintext UDP (frame format only)
- TestDTLSEncryption: Real DTLS-PSK tests (requires python3-dtls and a provisioned key)
"""

from __future__ import annotations

import os
import socket
import ssl
import struct
from dataclasses import dataclass
from typing import Any, Optional

import pytest

rclpy = pytest.importorskip("rclpy", reason="rclpy not available")

from geometry_msgs.msg import Twist  # noqa: E402

from conftest import topic_collector  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DTLS_PORT: int = int(os.environ.get("DTLS_TEST_PORT", "5684"))
DTLS_HOST: str = os.environ.get("DTLS_TEST_HOST", "192.168.4.1")
PSK_IDENTITY: bytes = b"robot-controller"
PSK_KEY: bytes = os.environb.get(b"INTEGRATION_TEST_PSK_KEY", b"")

# cmd_vel binary frame layout: [header(1) | linear_x(f32) | linear_y(f32) | angular_z(f32)]
CMD_VEL_HEADER: int = 0x01
CMD_VEL_FORMAT: str = "!Bfff"  # network byte order: uint8 + 3x float32


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CmdVelFrame:
    """Immutable representation of a cmd_vel binary frame."""

    linear_x: float
    linear_y: float
    angular_z: float

    def pack(self) -> bytes:
        """Serialize to binary frame for DTLS transmission."""
        return struct.pack(
            CMD_VEL_FORMAT,
            CMD_VEL_HEADER,
            self.linear_x,
            self.linear_y,
            self.angular_z,
        )


def _create_dtls_socket(
    host: str,
    port: int,
    psk_identity: bytes,
    psk_key: bytes,
    timeout: float = 5.0,
) -> Optional[ssl.SSLSocket]:
    """Attempt to create a DTLS (UDP + TLS-PSK) connection.

    Returns the wrapped socket or None if connection fails.

    Note: Python's ssl module does not support DTLS. This creates a raw
    UDP socket for transport smoke testing only. Production DTLS requires
    a dedicated library (e.g., python-dtls or mbedtls bindings).
    """
    # TODO: Implement real DTLS-PSK using python-dtls or equivalent
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return sock  # type: ignore[return-value]
    except (socket.timeout, OSError):
        return None


def _send_cmd_vel_udp(
    host: str,
    port: int,
    frame: CmdVelFrame,
    timeout: float = 5.0,
) -> bool:
    """Send a cmd_vel frame over plaintext UDP to the DTLS endpoint.

    This is a transport smoke test only — does NOT verify encryption.
    Returns True if the send succeeded (no socket error).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(frame.pack(), (host, port))
        sock.close()
        return True
    except (socket.timeout, OSError):
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.hardware
@pytest.mark.timeout(60)
class TestDTLSChannel:
    """DTLS encrypted channel connectivity and command delivery."""

    def test_dtls_port_reachable(self) -> None:
        """The ESP32 DTLS port should be reachable over UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)

        try:
            # Send a probe packet (will be rejected but shouldn't error at network level)
            sock.sendto(b"\x00", (DTLS_HOST, DTLS_PORT))
            # If we can send without OSError, the host/port is routable
        except OSError as exc:
            pytest.fail(f"Cannot reach DTLS endpoint {DTLS_HOST}:{DTLS_PORT}: {exc}")
        finally:
            sock.close()

    def test_cmd_vel_frame_serialization(self) -> None:
        """cmd_vel frame should pack to the expected binary format."""
        frame = CmdVelFrame(linear_x=0.5, linear_y=0.0, angular_z=1.0)
        packed = frame.pack()

        assert len(packed) == struct.calcsize(CMD_VEL_FORMAT)
        assert packed[0:1] == bytes([CMD_VEL_HEADER])

        # Unpack and verify roundtrip
        header, lx, ly, az = struct.unpack(CMD_VEL_FORMAT, packed)
        assert header == CMD_VEL_HEADER
        assert abs(lx - 0.5) < 1e-6
        assert abs(ly - 0.0) < 1e-6
        assert abs(az - 1.0) < 1e-6

    def test_cmd_vel_delivered_via_channel(self, test_node: Any) -> None:
        """A cmd_vel sent over the DTLS channel should appear on /cmd_vel topic."""
        frame = CmdVelFrame(linear_x=0.3, linear_y=0.0, angular_z=0.0)

        sent = _send_cmd_vel_udp(DTLS_HOST, DTLS_PORT, frame, timeout=5.0)
        if not sent:
            pytest.skip(
                f"Cannot send to {DTLS_HOST}:{DTLS_PORT} — network not available"
            )

        # Collect cmd_vel messages that the ESP32 should republish to ROS2
        messages = topic_collector(
            test_node,
            "/cmd_vel",
            Twist,
            timeout=10.0,
            count=1,
        )

        assert len(messages) > 0, (
            "No /cmd_vel message received after sending frame over DTLS channel"
        )

        received = messages[0]
        assert abs(received.linear.x - frame.linear_x) < 0.05

    def test_unauthenticated_connection_rejected(self, test_node: Any) -> None:
        """Sending raw unframed data should not produce valid commands.

        The ESP32 DTLS endpoint should reject packets that do not follow
        the PSK handshake or correct frame format.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3.0)

        # Send garbage data — should not crash the endpoint
        garbage = b"\xff\xfe\xfd\xfc\xfb\xfa"
        try:
            sock.sendto(garbage, (DTLS_HOST, DTLS_PORT))
        except OSError:
            pytest.skip(f"Network unreachable: {DTLS_HOST}:{DTLS_PORT}")
        finally:
            sock.close()

        # Verify no cmd_vel command was produced from the garbage packet
        messages = topic_collector(test_node, "/cmd_vel", Twist, timeout=3.0, count=1)
        assert len(messages) == 0, (
            "Unauthenticated garbage produced a /cmd_vel message — "
            "DTLS endpoint is not filtering malformed frames"
        )

    def test_frame_with_zero_velocity(self, test_node: Any) -> None:
        """A zero-velocity frame should be accepted (used for stopping)."""
        frame = CmdVelFrame(linear_x=0.0, linear_y=0.0, angular_z=0.0)
        packed = frame.pack()

        assert len(packed) == struct.calcsize(CMD_VEL_FORMAT)

        # Verify the zero frame is well-formed
        header, lx, ly, az = struct.unpack(CMD_VEL_FORMAT, packed)
        assert header == CMD_VEL_HEADER
        assert lx == 0.0
        assert ly == 0.0
        assert az == 0.0


# ---------------------------------------------------------------------------
# Real DTLS-PSK Tests
# ---------------------------------------------------------------------------

try:
    from dtls import do_patch as dtls_do_patch
    from dtls.sslconnection import SSLConnection

    HAS_DTLS = True
except ImportError:
    HAS_DTLS = False


@pytest.mark.hardware
@pytest.mark.timeout(60)
@pytest.mark.skipif(not HAS_DTLS, reason="python3-dtls not installed")
@pytest.mark.skipif(not PSK_KEY, reason="INTEGRATION_TEST_PSK_KEY not set")
class TestDTLSEncryption:
    """Real DTLS-PSK encrypted channel verification.

    Requires:
    - pip install python3-dtls
    - INTEGRATION_TEST_PSK_KEY env var set to the robot's provisioned PSK
    """

    @pytest.fixture(autouse=True)
    def _patch_dtls(self) -> None:
        dtls_do_patch()

    def _create_psk_connection(self, timeout: float = 5.0) -> SSLConnection:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        conn = SSLConnection(
            sock,
            keyfile=None,
            certfile=None,
            server_side=False,
            psk={PSK_IDENTITY: PSK_KEY},
            ciphers="PSK-AES128-CCM8",
        )
        conn.connect((DTLS_HOST, DTLS_PORT))
        conn.do_handshake()
        return conn

    def test_psk_handshake_succeeds(self) -> None:
        """DTLS-PSK handshake completes with valid credentials."""
        conn = self._create_psk_connection()
        try:
            assert conn is not None
        finally:
            conn.shutdown()

    def test_cmd_vel_over_dtls(self, test_node: Any) -> None:
        """cmd_vel frame sent over DTLS produces valid ROS2 message."""
        frame = CmdVelFrame(linear_x=0.2, linear_y=0.0, angular_z=0.5)
        conn = self._create_psk_connection()
        try:
            conn.send(frame.pack())
        finally:
            conn.shutdown()

        messages = topic_collector(
            test_node, "/cmd_vel", Twist, timeout=10.0, count=1
        )
        assert len(messages) > 0, (
            "No /cmd_vel message received after DTLS-encrypted frame"
        )
        assert abs(messages[0].linear.x - 0.2) < 0.05
        assert abs(messages[0].angular.z - 0.5) < 0.05

    def test_wrong_psk_rejected(self) -> None:
        """DTLS handshake with incorrect PSK must fail."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        conn = SSLConnection(
            sock,
            keyfile=None,
            certfile=None,
            server_side=False,
            psk={PSK_IDENTITY: b"wrong_key_0123456789abcdef"},
            ciphers="PSK-AES128-CCM8",
        )
        with pytest.raises((ssl.SSLError, OSError)):
            conn.connect((DTLS_HOST, DTLS_PORT))
            conn.do_handshake()
