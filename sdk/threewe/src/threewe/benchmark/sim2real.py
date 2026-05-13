# SPDX-License-Identifier: Apache-2.0
"""Sim2Real validation protocol — automated transfer tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


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
        passed = real_value < sim_value * test.pass_multiplier
        reason = (
            f"PASS: {real_value:.4f} < {sim_value:.4f} * {test.pass_multiplier}"
            if passed
            else f"FAIL: {real_value:.4f} >= {sim_value:.4f} * {test.pass_multiplier}"
        )
    elif test.comparison == "real_gt_sim_times_mult":
        passed = real_value > sim_value * test.pass_multiplier
        reason = (
            f"PASS: {real_value:.4f} > {sim_value:.4f} * {test.pass_multiplier}"
            if passed
            else f"FAIL: {real_value:.4f} <= {sim_value:.4f} * {test.pass_multiplier}"
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
