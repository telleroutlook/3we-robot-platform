# SPDX-License-Identifier: Apache-2.0
"""Sim2Real validation protocol — automated transfer tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

    from threewe.sim.noise import SensorNoiseModel


class TransferMetric(Enum):
    """Metric types for sim2real transfer validation."""

    ENDPOINT_ERROR = "endpoint_error"
    ANGLE_ERROR = "angle_error"
    SUCCESS_RATE = "success_rate"
    SPL = "spl"
    COLLISION_RATE = "collision_rate"


@dataclass(frozen=True)
class Sim2RealTest:
    """Definition of a single sim2real transfer test."""

    name: str
    description: str
    metric: TransferMetric
    pass_multiplier: float
    comparison: str = "real_lt_sim_times_mult"


STANDARD_TRANSFER_TESTS: list[Sim2RealTest] = [
    Sim2RealTest(
        name="straight_walk_5m",
        description="Drive 5m forward and measure endpoint error",
        metric=TransferMetric.ENDPOINT_ERROR,
        pass_multiplier=2.0,
        comparison="real_lt_sim_times_mult",
    ),
    Sim2RealTest(
        name="rotation_360",
        description="Rotate 360 degrees and measure final angle error",
        metric=TransferMetric.ANGLE_ERROR,
        pass_multiplier=1.0,
        comparison="real_lt_absolute",
    ),
    Sim2RealTest(
        name="obstacle_avoidance_3",
        description="Navigate past 3 obstacles, measure success rate",
        metric=TransferMetric.SUCCESS_RATE,
        pass_multiplier=0.7,
        comparison="real_gt_sim_times_mult",
    ),
    Sim2RealTest(
        name="pointnav_10m",
        description="Navigate to a point 10m away, measure SPL",
        metric=TransferMetric.SPL,
        pass_multiplier=0.6,
        comparison="real_gt_sim_times_mult",
    ),
    Sim2RealTest(
        name="dynamic_obstacle",
        description="Navigate with moving obstacles, measure collision rate",
        metric=TransferMetric.COLLISION_RATE,
        pass_multiplier=1.5,
        comparison="real_lt_sim_times_mult",
    ),
]


@dataclass(frozen=True)
class TransferResult:
    """Result of a single transfer test execution."""

    test_name: str
    sim_value: float
    real_value: float
    transfer_ratio: float
    passed: bool
    reason: str


@dataclass(frozen=True)
class Sim2RealReport:
    """Aggregated sim2real validation report."""

    results: tuple[TransferResult, ...]
    overall_passed: bool
    pass_rate: float
    timestamp: str


def evaluate_transfer(
    test: Sim2RealTest,
    sim_value: float,
    real_value: float,
) -> TransferResult:
    """Evaluate whether a single transfer test passes.

    Args:
        test: The transfer test definition.
        sim_value: Metric value from simulation.
        real_value: Metric value from real hardware.

    Returns:
        TransferResult with pass/fail and transfer ratio.
    """
    if sim_value == 0.0:
        transfer_ratio = float("inf") if real_value != 0.0 else 1.0
    else:
        transfer_ratio = real_value / sim_value

    if test.comparison == "real_lt_sim_times_mult":
        passed = real_value <= sim_value * test.pass_multiplier
        reason = (
            f"PASS: {real_value:.4f} <= {sim_value:.4f} * {test.pass_multiplier}"
            if passed
            else f"FAIL: {real_value:.4f} > {sim_value:.4f} * {test.pass_multiplier}"
        )
    elif test.comparison == "real_gt_sim_times_mult":
        passed = real_value >= sim_value * test.pass_multiplier
        reason = (
            f"PASS: {real_value:.4f} >= {sim_value:.4f} * {test.pass_multiplier}"
            if passed
            else f"FAIL: {real_value:.4f} < {sim_value:.4f} * {test.pass_multiplier}"
        )
    elif test.comparison == "real_lt_absolute":
        passed = real_value < test.pass_multiplier
        reason = (
            f"PASS: {real_value:.4f} < {test.pass_multiplier} (absolute)"
            if passed
            else f"FAIL: {real_value:.4f} >= {test.pass_multiplier} (absolute)"
        )
    else:
        passed = False
        reason = f"Unknown comparison type: {test.comparison}"

    return TransferResult(
        test_name=test.name,
        sim_value=sim_value,
        real_value=real_value,
        transfer_ratio=transfer_ratio,
        passed=passed,
        reason=reason,
    )


@dataclass
class Sim2RealValidator:
    """Executes sim2real transfer validation tests.

    Runs the standard test suite on both sim and real backends,
    then compares results to determine transfer quality.
    """

    tests: list[Sim2RealTest] = field(default_factory=lambda: list(STANDARD_TRANSFER_TESTS))

    async def run_test_sim_only(
        self,
        test: Sim2RealTest,
        backend: str = "gazebo",
        num_trials: int = 5,
    ) -> float:
        """Run a single test in simulation and return the metric value.

        This is the CI-friendly variant — runs sim baseline only.
        """
        from threewe import Robot

        values: list[float] = []

        async with Robot(backend=backend, auto_connect=True) as robot:
            for _ in range(num_trials):
                value = await self._execute_test(robot, test)
                values.append(value)

        return sum(values) / len(values) if values else 0.0

    async def validate(
        self,
        sim_backend: str = "gazebo",
        real_backend: str = "real",
        num_trials: int = 5,
    ) -> Sim2RealReport:
        """Run full sim2real validation comparing both backends."""
        results: list[TransferResult] = []

        for test in self.tests:
            sim_value = await self.run_test_sim_only(
                test, backend=sim_backend, num_trials=num_trials
            )
            real_value = await self.run_test_sim_only(
                test, backend=real_backend, num_trials=num_trials
            )
            result = evaluate_transfer(test, sim_value, real_value)
            results.append(result)

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        pass_rate = passed_count / total if total > 0 else 0.0

        return Sim2RealReport(
            results=tuple(results),
            overall_passed=pass_rate >= 0.8,
            pass_rate=pass_rate,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    async def _execute_test(self, robot: object, test: Sim2RealTest) -> float:
        """Execute a single test on a connected robot and return the metric."""

        if test.name == "straight_walk_5m":
            start = robot.get_pose()  # type: ignore[attr-defined]
            result = await robot.move_to(  # type: ignore[attr-defined]
                x=start.x + 5.0, y=start.y, timeout=30.0
            )
            end = robot.get_pose()  # type: ignore[attr-defined]
            target_x = start.x + 5.0
            return ((end.x - target_x) ** 2 + (end.y - start.y) ** 2) ** 0.5

        elif test.name == "rotation_360":
            import math

            start = robot.get_pose()  # type: ignore[attr-defined]
            target_theta = start.theta + 2 * math.pi
            await robot.move_to(  # type: ignore[attr-defined]
                x=start.x, y=start.y, theta=target_theta, timeout=15.0
            )
            end = robot.get_pose()  # type: ignore[attr-defined]
            angle_diff = abs(end.theta - start.theta) % (2 * math.pi)
            return min(angle_diff, 2 * math.pi - angle_diff) * (180.0 / math.pi)

        elif test.name == "obstacle_avoidance_3":
            successes = 0
            trials = 3
            for i in range(trials):
                result = await robot.move_to(  # type: ignore[attr-defined]
                    x=3.0 * (i + 1), y=0.0, timeout=20.0
                )
                if result.success:
                    successes += 1
            return successes / trials

        elif test.name == "pointnav_10m":
            import math

            start = robot.get_pose()  # type: ignore[attr-defined]
            goal_x = start.x + 10.0
            optimal = 10.0
            result = await robot.move_to(  # type: ignore[attr-defined]
                x=goal_x, y=start.y, timeout=60.0
            )
            if result.success and result.distance > 0:
                return optimal / result.distance
            return 0.0

        elif test.name == "dynamic_obstacle":
            collisions = 0
            trials = 5
            for i in range(trials):
                result = await robot.move_to(  # type: ignore[attr-defined]
                    x=2.0 * (i + 1), y=0.0, timeout=15.0
                )
                if result.reason == "collision":
                    collisions += 1
            return collisions / trials

        return 0.0


def _apply_sensor_degradation(
    value: float,
    test: Sim2RealTest,
    noise_model: SensorNoiseModel,
    rng: np.random.Generator,
) -> float:
    """Apply physically-grounded sensor noise to a test metric value.

    Maps each test type to the relevant noise source:
    - Position-based tests (endpoint, SPL): odometry slip
    - Rotation tests: IMU gyro drift
    - Rate-based tests (success, collision): compound odometry + heading
    """

    if test.metric == TransferMetric.ENDPOINT_ERROR:
        slip = rng.uniform(
            noise_model.odometry.slip_factor_min,
            noise_model.odometry.slip_factor_max,
        )
        return value + value * slip

    elif test.metric == TransferMetric.ANGLE_ERROR:
        gyro_drift = abs(rng.normal(0.0, noise_model.imu.gyro_stddev * 100))
        return value + gyro_drift

    elif test.metric == TransferMetric.SUCCESS_RATE:
        slip = rng.uniform(
            noise_model.odometry.slip_factor_min,
            noise_model.odometry.slip_factor_max,
        )
        return max(0.0, value * (1.0 - slip))

    elif test.metric == TransferMetric.SPL:
        slip = rng.uniform(
            noise_model.odometry.slip_factor_min,
            noise_model.odometry.slip_factor_max,
        )
        return max(0.0, value * (1.0 - slip * 0.5))

    elif test.metric == TransferMetric.COLLISION_RATE:
        heading_noise = abs(rng.normal(0.0, noise_model.imu.orientation_stddev * 10))
        return min(1.0, value + heading_noise * 0.3)

    return value


async def generate_demo_report(num_trials: int = 5, seed: int = 42) -> str:
    """Generate a demonstration Sim2Real report using the MockBackend.

    Runs the standard transfer test suite against the mock backend twice:
    - "sim": clean kinematic model (no sensor noise)
    - "real": same kinematic model + calibrated SensorNoiseModel

    The noise injection uses hardware-measured parameters (LD06 LiDAR,
    BNO055 IMU, mecanum wheel odometry) so transfer ratios reflect
    realistic sim-to-real degradation patterns.

    Returns:
        Formatted Markdown report string.
    """
    import numpy as np

    from threewe import Robot
    from threewe.sim.noise import SensorNoiseModel

    noise_model = SensorNoiseModel(seed=seed)
    rng = np.random.default_rng(seed)
    results: list[TransferResult] = []

    for test in STANDARD_TRANSFER_TESTS:
        sim_values: list[float] = []
        real_values: list[float] = []

        async with Robot(backend="mock", auto_connect=True) as sim_robot:
            for _ in range(num_trials):
                value = await Sim2RealValidator()._execute_test(sim_robot, test)
                sim_values.append(value)

        async with Robot(backend="mock", auto_connect=True) as real_robot:
            for _ in range(num_trials):
                value = await Sim2RealValidator()._execute_test(real_robot, test)
                value = _apply_sensor_degradation(value, test, noise_model, rng)
                real_values.append(value)

        sim_avg = sum(sim_values) / len(sim_values) if sim_values else 0.0
        real_avg = sum(real_values) / len(real_values) if real_values else 0.0

        result = evaluate_transfer(test, sim_avg, real_avg)
        results.append(result)

    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed_count / total if total > 0 else 0.0

    lines = [
        "# Sim2Real Transfer Validation Report (Demo)",
        "",
        f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "- **Sim Backend**: mock (ideal kinematic model, no sensor noise)",
        "- **Real Backend**: mock + SensorNoiseModel (calibrated from hardware)",
        f"- **Trials per test**: {num_trials}",
        "- **Noise parameters**: LD06 LiDAR σ=8mm, BNO055 gyro σ=0.0014 rad/s, odometry slip 5-15%",
        "",
        "## Transfer Test Results",
        "",
        "| Test | Sim Value | Real Value | Transfer Ratio | Status |",
        "|------|-----------|------------|----------------|--------|",
    ]

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(
            f"| {r.test_name} | {r.sim_value:.4f} | {r.real_value:.4f} "
            f"| {r.transfer_ratio:.3f} | {'✅' if r.passed else '❌'} {status} |"
        )

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- **Tests passed**: {passed_count}/{total} ({pass_rate:.0%})",
            f"- **Overall**: {'PASS' if pass_rate >= 0.8 else 'FAIL'} (threshold: 80%)",
            "",
            "## Pass Criteria",
            "",
        ]
    )

    for test in STANDARD_TRANSFER_TESTS:
        lines.append(
            f"- **{test.name}**: {test.description} "
            f"(criterion: {test.comparison}, multiplier: {test.pass_multiplier})"
        )

    lines.extend(
        [
            "",
            "---",
            "*This report uses calibrated sensor noise models (threewe.sim.noise) to*",
            "*simulate real-hardware degradation on top of the MockBackend kinematic model.*",
            '*Replace with `backend="gazebo"` and `backend="real"` for actual '
            "Sim2Real validation.*",
        ]
    )

    return "\n".join(lines)
