# SPDX-License-Identifier: Apache-2.0
"""Benchmark runner — executes evaluation episodes and collects metrics."""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from threewe.benchmark.metrics import compute_spl, compute_success_rate


@dataclass
class EpisodeResult:
    """Result of a single benchmark episode."""

    episode_id: int
    success: bool
    duration: float
    path_length: float
    optimal_length: float = 0.0
    coverage: float = 0.0
    reason: str = ""


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results."""

    task: str
    backend: str
    num_episodes: int
    success_rate: float
    spl: float
    avg_duration: float
    avg_path_length: float
    coverage: float = 0.0
    episodes: list[EpisodeResult] = field(default_factory=list)
    timestamp: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())


class BenchmarkRunner:
    """Runs standardized benchmark episodes on the robot."""

    def __init__(
        self,
        backend: str = "gazebo",
        scene: str = "office_v2",
    ) -> None:
        self._backend = backend
        self._scene = scene

    async def run_pointnav(
        self,
        num_episodes: int = 100,
        arena_size: float = 5.0,
        seed: int = 42,
    ) -> BenchmarkReport:
        """Run point-to-point navigation benchmark."""
        import numpy as np

        from threewe import Robot

        rng = np.random.default_rng(seed)
        episodes: list[EpisodeResult] = []

        async with Robot(backend=self._backend, auto_connect=True) as robot:
            for ep in range(num_episodes):
                goal_x = float(rng.uniform(-arena_size * 0.8, arena_size * 0.8))
                goal_y = float(rng.uniform(-arena_size * 0.8, arena_size * 0.8))

                start_pose = robot.get_pose()
                optimal = math.sqrt((goal_x - start_pose.x) ** 2 + (goal_y - start_pose.y) ** 2)

                start_time = time.time()
                result = await robot.move_to(x=goal_x, y=goal_y, timeout=30.0)
                duration = time.time() - start_time

                episodes.append(
                    EpisodeResult(
                        episode_id=ep,
                        success=result.success,
                        duration=duration,
                        path_length=result.distance,
                        optimal_length=optimal,
                        reason=result.reason,
                    )
                )

        return self._build_report("pointnav", episodes)

    async def run_exploration(
        self,
        num_episodes: int = 10,
        timeout_per_episode: float = 120.0,
    ) -> BenchmarkReport:
        """Run exploration coverage benchmark."""
        from threewe import Robot

        episodes: list[EpisodeResult] = []

        async with Robot(backend=self._backend, auto_connect=True) as robot:
            for ep in range(num_episodes):
                start_time = time.time()
                result = await robot.explore(timeout=timeout_per_episode)
                duration = time.time() - start_time

                episodes.append(
                    EpisodeResult(
                        episode_id=ep,
                        success=result.coverage >= 0.8,
                        duration=duration,
                        path_length=0.0,
                        coverage=result.coverage,
                        reason="timed_out" if result.timed_out else "completed",
                    )
                )

        return self._build_report("exploration", episodes)

    def _build_report(self, task: str, episodes: list[EpisodeResult]) -> BenchmarkReport:
        successes = [ep.success for ep in episodes]
        path_lengths = [ep.path_length for ep in episodes]
        optimal_lengths = [ep.optimal_length for ep in episodes]
        durations = [ep.duration for ep in episodes]
        coverages = [ep.coverage for ep in episodes]

        return BenchmarkReport(
            task=task,
            backend=self._backend,
            num_episodes=len(episodes),
            success_rate=compute_success_rate(successes),
            spl=compute_spl(successes, path_lengths, optimal_lengths),
            avg_duration=sum(durations) / len(durations) if durations else 0.0,
            avg_path_length=sum(path_lengths) / len(path_lengths) if path_lengths else 0.0,
            coverage=sum(coverages) / len(coverages) if coverages else 0.0,
            episodes=episodes,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )


def run_benchmark_cli(task: str, episodes: int, backend: str, scene: str) -> None:
    """CLI entry point for benchmark execution."""
    runner = BenchmarkRunner(backend=backend, scene=scene)

    print(f"Running {task} benchmark: {episodes} episodes on {backend}")
    print("=" * 50)

    if task == "pointnav":
        report = asyncio.run(runner.run_pointnav(num_episodes=episodes))
    elif task == "exploration":
        report = asyncio.run(runner.run_exploration(num_episodes=episodes))
    else:
        print(f"Unknown task: {task}")
        return

    print("\nResults:")
    print(f"  Success Rate: {report.success_rate * 100:.1f}%")
    print(f"  SPL:          {report.spl:.3f}")
    print(f"  Avg Duration: {report.avg_duration:.2f}s")
    print(f"  Avg Path Len: {report.avg_path_length:.2f}m")
    if report.coverage > 0:
        print(f"  Avg Coverage: {report.coverage * 100:.1f}%")

    output_path = Path(f"benchmark_{task}_{backend}.json")
    report.save(output_path)
    print(f"\nReport saved to: {output_path}")
