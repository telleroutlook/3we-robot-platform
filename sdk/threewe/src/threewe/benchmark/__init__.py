# SPDX-License-Identifier: Apache-2.0
"""Benchmark framework for standardized robot evaluation.

Provides reproducible evaluation tasks with standard metrics:
- PointNav: Point-to-point navigation (SPL, Success Rate)
- ObjectNav: Object-goal navigation (SPL, Success Rate)
- Exploration: Coverage exploration (Coverage %, Duration)

Usage:
    threewe benchmark run --task pointnav --episodes 100 --backend gazebo
"""

from threewe.benchmark.metrics import compute_spl, compute_success_rate
from threewe.benchmark.runner import BenchmarkRunner

__all__ = ["BenchmarkRunner", "compute_spl", "compute_success_rate"]
