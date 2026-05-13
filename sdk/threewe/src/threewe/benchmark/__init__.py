# SPDX-License-Identifier: Apache-2.0
"""Benchmark framework for standardized robot evaluation.

Provides reproducible evaluation tasks with standard metrics:
- PointNav: Point-to-point navigation (SPL, Success Rate)
- ObjectNav: Object-goal navigation (SPL, Success Rate)
- Exploration: Coverage exploration (Coverage %, Duration)

Usage:
    threewe benchmark run --task pointnav --episodes 100 --backend gazebo
    threewe benchmark compare --result result.json --baseline nav2_pointnav_office
"""

from threewe.benchmark.baselines import compare_to_baseline, list_baselines
from threewe.benchmark.leaderboard import LeaderboardEntry, rank_entries, validate_submission
from threewe.benchmark.metrics import compute_spl, compute_success_rate
from threewe.benchmark.objectnav_runner import (
    ObjectNavEpisodeConfig,
    generate_objectnav_episodes,
    run_objectnav_episode,
)
from threewe.benchmark.runner import BenchmarkRunner
from threewe.benchmark.tasks import get_task, list_tasks

__all__ = [
    "BenchmarkRunner",
    "LeaderboardEntry",
    "ObjectNavEpisodeConfig",
    "compare_to_baseline",
    "compute_spl",
    "compute_success_rate",
    "generate_objectnav_episodes",
    "get_task",
    "list_baselines",
    "list_tasks",
    "rank_entries",
    "run_objectnav_episode",
    "validate_submission",
]
