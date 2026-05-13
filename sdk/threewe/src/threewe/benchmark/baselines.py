# SPDX-License-Identifier: Apache-2.0
"""Benchmark baselines — reference results for comparison."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineResult:
    """A baseline benchmark result for comparison."""

    task: str
    scene: str
    agent: str
    num_episodes: int
    success_rate: float
    spl: float
    avg_duration: float
    coverage: float = 0.0


BASELINES: dict[str, BaselineResult] = {
    "nav2_pointnav_office": BaselineResult(
        task="pointnav",
        scene="office_v2",
        agent="nav2_default",
        num_episodes=100,
        success_rate=0.82,
        spl=0.65,
        avg_duration=12.3,
    ),
    "nav2_pointnav_apartment": BaselineResult(
        task="pointnav",
        scene="apartment_v1",
        agent="nav2_default",
        num_episodes=100,
        success_rate=0.68,
        spl=0.52,
        avg_duration=15.7,
    ),
    "nav2_pointnav_corridor": BaselineResult(
        task="pointnav",
        scene="corridor_v1",
        agent="nav2_default",
        num_episodes=100,
        success_rate=0.91,
        spl=0.78,
        avg_duration=18.5,
    ),
    "frontier_exploration_office": BaselineResult(
        task="exploration",
        scene="office_v2",
        agent="frontier_exploration",
        num_episodes=10,
        success_rate=0.7,
        spl=0.0,
        avg_duration=95.0,
        coverage=0.85,
    ),
    "frontier_exploration_corridor": BaselineResult(
        task="exploration",
        scene="corridor_v1",
        agent="frontier_exploration",
        num_episodes=10,
        success_rate=0.9,
        spl=0.0,
        avg_duration=72.0,
        coverage=0.92,
    ),
}


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing against a baseline."""

    baseline_name: str
    baseline: BaselineResult
    success_rate_delta: float
    spl_delta: float
    duration_delta: float
    coverage_delta: float
    improved: bool


def compare_to_baseline(
    baseline_name: str,
    success_rate: float,
    spl: float,
    avg_duration: float,
    coverage: float = 0.0,
) -> ComparisonResult:
    """Compare new results to a stored baseline.

    Args:
        baseline_name: Key in BASELINES dict.
        success_rate: New success rate.
        spl: New SPL value.
        avg_duration: New average duration.
        coverage: New coverage (for exploration tasks).

    Returns:
        ComparisonResult with deltas and improvement flag.

    Raises:
        ValueError: If baseline name is unknown.
    """
    if baseline_name not in BASELINES:
        raise ValueError(
            f"Unknown baseline: '{baseline_name}'. Available: {list(BASELINES.keys())}"
        )

    baseline = BASELINES[baseline_name]
    sr_delta = success_rate - baseline.success_rate
    spl_delta = spl - baseline.spl
    dur_delta = avg_duration - baseline.avg_duration
    cov_delta = coverage - baseline.coverage

    improved = sr_delta >= 0 and spl_delta >= 0

    return ComparisonResult(
        baseline_name=baseline_name,
        baseline=baseline,
        success_rate_delta=sr_delta,
        spl_delta=spl_delta,
        duration_delta=dur_delta,
        coverage_delta=cov_delta,
        improved=improved,
    )


def list_baselines() -> list[str]:
    """Return names of all available baselines."""
    return list(BASELINES.keys())
