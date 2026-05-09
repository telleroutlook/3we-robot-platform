#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Hardware validation runner — orchestrates subsystem tests on a physical robot.

Requires:
  - ROS2 Humble sourced
  - micro-ROS agent running
  - Robot powered on and connected

Usage:
  python3 scripts/run-hardware-validation.py              # run all subsystems
  python3 scripts/run-hardware-validation.py --subsystem motors
  python3 scripts/run-hardware-validation.py --subsystem encoders
  python3 scripts/run-hardware-validation.py --subsystem ultrasonic
  python3 scripts/run-hardware-validation.py --output results.json
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "tests" / "hardware_validation" / "scripts"

TIMEOUT_SECONDS = 60


@dataclass
class TestResult:
    subsystem: str
    test_name: str
    passed: bool
    duration_s: float
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    timestamp: str
    duration_s: float
    results: list[TestResult] = field(default_factory=list)
    overall_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_s": self.duration_s,
            "overall_passed": self.overall_passed,
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [
                {
                    "subsystem": r.subsystem,
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration_s": round(r.duration_s, 3),
                    "message": r.message,
                    "data": r.data,
                }
                for r in self.results
            ],
        }


def check_ros2_available() -> bool:
    """Verify ROS2 environment is sourced and topics are visible."""
    try:
        result = subprocess.run(
            ["ros2", "topic", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_robot_connected() -> bool:
    """Check if the robot node is publishing topics."""
    try:
        result = subprocess.run(
            ["ros2", "topic", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        topics = result.stdout.strip().split("\n")
        return "/odom" in topics or "/battery_state" in topics
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_motor_sweep(report: ValidationReport) -> None:
    """Run motor sweep test and verify motors respond."""
    script = SCRIPTS_DIR / "motor_sweep.py"
    if not script.exists():
        report.results.append(
            TestResult(
                subsystem="motors",
                test_name="motor_sweep",
                passed=False,
                duration_s=0,
                message=f"Script not found: {script}",
            )
        )
        return

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script), "motions"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        duration = time.time() - start

        passed = result.returncode == 0
        report.results.append(
            TestResult(
                subsystem="motors",
                test_name="motor_sweep_motions",
                passed=passed,
                duration_s=duration,
                message=result.stderr if not passed else "All motions completed",
            )
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        report.results.append(
            TestResult(
                subsystem="motors",
                test_name="motor_sweep_motions",
                passed=False,
                duration_s=duration,
                message=f"Timeout after {TIMEOUT_SECONDS}s",
            )
        )
        stop_motors()


def run_encoder_calibration(report: ValidationReport) -> None:
    """Run encoder calibration and verify counts are reasonable."""
    script = SCRIPTS_DIR / "encoder_calibrate.py"
    if not script.exists():
        report.results.append(
            TestResult(
                subsystem="encoders",
                test_name="encoder_calibrate",
                passed=False,
                duration_s=0,
                message=f"Script not found: {script}",
            )
        )
        return

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        duration = time.time() - start

        passed = result.returncode == 0
        report.results.append(
            TestResult(
                subsystem="encoders",
                test_name="encoder_calibrate",
                passed=passed,
                duration_s=duration,
                message=result.stderr if not passed else "Encoder calibration complete",
            )
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        report.results.append(
            TestResult(
                subsystem="encoders",
                test_name="encoder_calibrate",
                passed=False,
                duration_s=duration,
                message=f"Timeout after {TIMEOUT_SECONDS}s",
            )
        )


def run_ultrasonic_log(report: ValidationReport) -> None:
    """Run ultrasonic sensor logging and verify readings are within range."""
    script = SCRIPTS_DIR / "ultrasonic_log.py"
    if not script.exists():
        report.results.append(
            TestResult(
                subsystem="ultrasonic",
                test_name="ultrasonic_log",
                passed=False,
                duration_s=0,
                message=f"Script not found: {script}",
            )
        )
        return

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        duration = time.time() - start

        passed = result.returncode == 0
        report.results.append(
            TestResult(
                subsystem="ultrasonic",
                test_name="ultrasonic_log",
                passed=passed,
                duration_s=duration,
                message=result.stderr if not passed else "All sensors responding",
            )
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        report.results.append(
            TestResult(
                subsystem="ultrasonic",
                test_name="ultrasonic_log",
                passed=False,
                duration_s=duration,
                message=f"Timeout after {TIMEOUT_SECONDS}s",
            )
        )


def run_battery_check(report: ValidationReport) -> None:
    """Verify battery topic is publishing reasonable values."""
    start = time.time()
    try:
        result = subprocess.run(
            ["ros2", "topic", "echo", "/battery_state", "--once"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        duration = time.time() - start

        if result.returncode != 0:
            report.results.append(
                TestResult(
                    subsystem="battery",
                    test_name="battery_topic_check",
                    passed=False,
                    duration_s=duration,
                    message="Failed to read /battery_state",
                )
            )
            return

        output = result.stdout
        voltage = None
        for line in output.split("\n"):
            if "voltage:" in line:
                try:
                    voltage = float(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass

        if voltage is None:
            report.results.append(
                TestResult(
                    subsystem="battery",
                    test_name="battery_topic_check",
                    passed=False,
                    duration_s=duration,
                    message="Could not parse voltage from topic",
                )
            )
        elif 6.0 <= voltage <= 8.5:
            report.results.append(
                TestResult(
                    subsystem="battery",
                    test_name="battery_topic_check",
                    passed=True,
                    duration_s=duration,
                    message=f"Battery voltage: {voltage:.2f}V (normal range)",
                    data={"voltage": voltage},
                )
            )
        else:
            report.results.append(
                TestResult(
                    subsystem="battery",
                    test_name="battery_topic_check",
                    passed=False,
                    duration_s=duration,
                    message=f"Battery voltage {voltage:.2f}V outside expected range (6.0-8.5V)",
                    data={"voltage": voltage},
                )
            )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        report.results.append(
            TestResult(
                subsystem="battery",
                test_name="battery_topic_check",
                passed=False,
                duration_s=duration,
                message="Timeout waiting for /battery_state",
            )
        )


def run_estop_check(report: ValidationReport) -> None:
    """Verify E-stop state is readable and robot is in normal state."""
    start = time.time()
    try:
        result = subprocess.run(
            ["ros2", "topic", "echo", "/emergency_stop_state", "--once"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        duration = time.time() - start

        if result.returncode != 0:
            report.results.append(
                TestResult(
                    subsystem="safety",
                    test_name="estop_state_check",
                    passed=False,
                    duration_s=duration,
                    message="Failed to read /emergency_stop_state",
                )
            )
            return

        output = result.stdout
        stopped = "stopped: true" in output.lower() or "stopped: True" in output

        report.results.append(
            TestResult(
                subsystem="safety",
                test_name="estop_state_check",
                passed=not stopped,
                duration_s=duration,
                message="E-stop is ACTIVE (release button first)"
                if stopped
                else "Safety system normal",
            )
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        report.results.append(
            TestResult(
                subsystem="safety",
                test_name="estop_state_check",
                passed=False,
                duration_s=duration,
                message="Timeout waiting for /emergency_stop_state",
            )
        )


def stop_motors() -> None:
    """Emergency: publish zero velocity to stop all motors."""
    try:
        subprocess.run(
            [
                "ros2",
                "topic",
                "pub",
                "--once",
                "/cmd_vel",
                "geometry_msgs/msg/Twist",
                "{linear: {x: 0, y: 0, z: 0}, angular: {x: 0, y: 0, z: 0}}",
            ],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


SUBSYSTEM_RUNNERS = {
    "safety": run_estop_check,
    "battery": run_battery_check,
    "motors": run_motor_sweep,
    "encoders": run_encoder_calibration,
    "ultrasonic": run_ultrasonic_log,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Robot platform hardware validation")
    parser.add_argument(
        "--subsystem",
        choices=list(SUBSYSTEM_RUNNERS.keys()),
        help="Run only a specific subsystem test",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help=f"Per-test timeout in seconds (default: {TIMEOUT_SECONDS})",
    )
    args = parser.parse_args()

    global TIMEOUT_SECONDS
    TIMEOUT_SECONDS = args.timeout

    # Graceful shutdown on Ctrl+C
    def signal_handler(sig: int, frame: Any) -> None:
        print("\nInterrupted — stopping motors...")
        stop_motors()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    # Pre-flight checks
    print("=== Hardware Validation Runner ===\n")

    print("Checking ROS2 environment...")
    if not check_ros2_available():
        print("ERROR: ROS2 not available. Source your ROS2 workspace first.")
        sys.exit(1)
    print("  ROS2: OK")

    print("Checking robot connection...")
    if not check_robot_connected():
        print("ERROR: Robot topics not found. Ensure:")
        print("  1. Robot is powered on")
        print("  2. micro-ROS agent is running")
        print("  3. Serial cable is connected")
        sys.exit(1)
    print("  Robot: Connected\n")

    # Run tests
    start_time = time.time()
    report = ValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_s=0,
    )

    runners = (
        {args.subsystem: SUBSYSTEM_RUNNERS[args.subsystem]}
        if args.subsystem
        else SUBSYSTEM_RUNNERS
    )

    for name, runner in runners.items():
        print(f"--- Testing: {name} ---")
        runner(report)
        last_result = report.results[-1] if report.results else None
        if last_result:
            status = "PASS" if last_result.passed else "FAIL"
            print(f"  [{status}] {last_result.test_name}: {last_result.message}")
        print()

    report.duration_s = round(time.time() - start_time, 2)
    report.overall_passed = all(r.passed for r in report.results)

    # Summary
    print("=== Results ===\n")
    passed = sum(1 for r in report.results if r.passed)
    failed = sum(1 for r in report.results if not r.passed)
    total = len(report.results)

    for r in report.results:
        icon = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.subsystem}/{r.test_name} ({r.duration_s:.1f}s)")
        if not r.passed:
            print(f"        {r.message}")

    print(f"\nTotal: {passed}/{total} passed, {failed} failed ({report.duration_s}s)")

    if report.overall_passed:
        print("\nAll hardware validation tests PASSED.")
    else:
        print("\nSome tests FAILED. See details above.")

    # Write JSON report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport written to: {args.output}")

    # Ensure motors are stopped
    stop_motors()

    sys.exit(0 if report.overall_passed else 1)


if __name__ == "__main__":
    main()
