# SPDX-License-Identifier: Apache-2.0
"""Benchmark task definitions — pluggable evaluation protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from threewe.benchmark.runner import EpisodeResult


class BenchmarkTask(Protocol):
    """Protocol for pluggable benchmark tasks."""

    @property
    def name(self) -> str: ...

    @property
    def metrics(self) -> tuple[str, ...]: ...

    @property
    def valid_scenes(self) -> tuple[str, ...]: ...

    def is_success(self, episode: EpisodeResult) -> bool: ...


@dataclass(frozen=True)
class PointNavTask:
    """Point-to-point navigation task.

    Metrics: SPL, success_rate
    Success condition: robot reaches within 0.5m of goal.
    """

    name: str = "pointnav"
    metrics: tuple[str, ...] = ("spl", "success_rate", "avg_duration")
    valid_scenes: tuple[str, ...] = ("office_v2", "apartment_v1", "corridor_v1")
    success_threshold: float = 0.5

    def is_success(self, episode: EpisodeResult) -> bool:
        return episode.success


@dataclass(frozen=True)
class ObjectNavTask:
    """Object-goal navigation task.

    Robot must navigate to an object of a specified category.
    Metrics: SPL, success_rate
    """

    name: str = "objectnav"
    metrics: tuple[str, ...] = ("spl", "success_rate", "avg_duration")
    valid_scenes: tuple[str, ...] = ("office_v2", "apartment_v1")
    object_categories: tuple[str, ...] = (
        "chair",
        "desk",
        "door",
        "plant",
        "monitor",
        "couch",
        "table",
        "shelf",
        "refrigerator",
        "bed",
    )

    def is_success(self, episode: EpisodeResult) -> bool:
        return episode.success


@dataclass(frozen=True)
class ExplorationTask:
    """Coverage exploration task.

    Robot must maximize area coverage within a time limit.
    Metrics: coverage_pct, duration
    """

    name: str = "exploration"
    metrics: tuple[str, ...] = ("coverage", "avg_duration", "success_rate")
    valid_scenes: tuple[str, ...] = ("office_v2", "apartment_v1", "corridor_v1")
    coverage_threshold: float = 0.8

    def is_success(self, episode: EpisodeResult) -> bool:
        return episode.coverage >= self.coverage_threshold


TASK_REGISTRY: dict[str, BenchmarkTask] = {
    "pointnav": PointNavTask(),
    "objectnav": ObjectNavTask(),
    "exploration": ExplorationTask(),
}


def get_task(name: str) -> BenchmarkTask:
    """Get a benchmark task by name.

    Raises:
        ValueError: If task name is unknown.
    """
    if name not in TASK_REGISTRY:
        raise ValueError(f"Unknown task: '{name}'. Available: {list(TASK_REGISTRY.keys())}")
    return TASK_REGISTRY[name]


def list_tasks() -> list[str]:
    """Return names of all registered benchmark tasks."""
    return list(TASK_REGISTRY.keys())
