# SPDX-License-Identifier: Apache-2.0
"""
Integration test for the robot_diagnostics node.

Verifies that the diagnostics node:
1. Starts without errors
2. Publishes DiagnosticArray on /diagnostics
3. Correctly aggregates battery and safety data
"""

import pytest
import time

from diagnostic_msgs.msg import DiagnosticArray

# Mark as simulation test (no hardware required)
pytestmark = [pytest.mark.simulation]

_NODE_STARTUP_TIMEOUT = 10.0
_NODE_STARTUP_POLL_INTERVAL = 0.2


def _wait_for_node_ready(test_node, topic: str, msg_type, timeout: float) -> None:
    """Poll until at least one message arrives on topic, confirming node is alive."""
    import rclpy

    deadline = time.monotonic() + timeout
    received = []

    def _cb(msg):
        received.append(msg)

    sub = test_node.create_subscription(msg_type, topic, _cb, 10)
    try:
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(test_node, timeout_sec=_NODE_STARTUP_POLL_INTERVAL)
    finally:
        test_node.destroy_subscription(sub)

    if not received:
        raise TimeoutError(f"Node did not publish on '{topic}' within {timeout}s")


@pytest.fixture
def diagnostics_node(ros2_context, test_node):
    """Launch diagnostics node in background, wait until it publishes."""
    import subprocess
    import signal

    proc = subprocess.Popen(
        [
            "ros2",
            "run",
            "robot_diagnostics",
            "diagnostics_node",
            "--ros-args",
            "-p",
            "robot_id:=test-robot",
            "-p",
            "publish_rate_hz:=10.0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_node_ready(
            test_node, "/diagnostics", DiagnosticArray, _NODE_STARTUP_TIMEOUT
        )
    except TimeoutError:
        proc.kill()
        proc.wait()
        raise

    yield proc
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def test_diagnostics_publishes(
    ros2_context, test_node, diagnostics_node, collect_topics
):
    """Verify diagnostics node publishes DiagnosticArray."""
    from diagnostic_msgs.msg import DiagnosticArray

    msgs = collect_topics("/diagnostics", DiagnosticArray, count=3, timeout=5.0)
    assert len(msgs) >= 1, "No DiagnosticArray messages received"

    diag = msgs[0]
    assert len(diag.status) > 0, "DiagnosticArray has no status entries"

    names = [s.name for s in diag.status]
    assert any("system" in n for n in names), f"No system status found in {names}"


def test_diagnostics_reports_battery(
    ros2_context, test_node, diagnostics_node, collect_topics
):
    """Verify diagnostics includes battery status after publishing battery data."""
    import rclpy
    from diagnostic_msgs.msg import DiagnosticArray
    from sensor_msgs.msg import BatteryState

    pub = test_node.create_publisher(BatteryState, "/battery_state", 10)

    battery_msg = BatteryState()
    battery_msg.percentage = 0.75
    battery_msg.voltage = 7.8

    for _ in range(10):
        pub.publish(battery_msg)
        rclpy.spin_once(test_node, timeout_sec=0.1)

    msgs = collect_topics("/diagnostics", DiagnosticArray, count=5, timeout=5.0)
    assert len(msgs) >= 1

    battery_found = False
    for diag in msgs:
        for status in diag.status:
            if "battery" in status.name:
                battery_found = True
                assert "OK" in status.message or "75" in status.message
                break

    assert battery_found, "Battery status not found in diagnostics"


def test_diagnostics_reports_estop(
    ros2_context, test_node, diagnostics_node, collect_topics
):
    """Verify diagnostics reflects E-stop state."""
    import rclpy
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
    from std_msgs.msg import Bool

    pub = test_node.create_publisher(Bool, "/emergency_stop_state", 10)

    estop_msg = Bool()
    estop_msg.data = True

    for _ in range(10):
        pub.publish(estop_msg)
        rclpy.spin_once(test_node, timeout_sec=0.1)

    msgs = collect_topics("/diagnostics", DiagnosticArray, count=3, timeout=5.0)
    assert len(msgs) >= 1

    estop_found = False
    for diag in msgs:
        for status in diag.status:
            if "safety" in status.name:
                estop_found = True
                assert status.level == DiagnosticStatus.ERROR
                assert "E-STOP" in status.message
                break

    assert estop_found, "Safety/E-stop status not found in diagnostics"
