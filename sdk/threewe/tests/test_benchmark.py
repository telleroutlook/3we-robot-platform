# SPDX-License-Identifier: Apache-2.0
"""Tests for the benchmark framework: metrics, runner, and report."""

from __future__ import annotations

import json

from threewe.benchmark.metrics import compute_coverage, compute_spl, compute_success_rate
from threewe.benchmark.runner import BenchmarkReport, BenchmarkRunner, EpisodeResult


class TestComputeSPL:
    def test_empty_list(self):
        assert compute_spl([], [], []) == 0.0

    def test_all_success_optimal_paths(self):
        successes = [True, True, True]
        path_lengths = [5.0, 3.0, 4.0]
        optimal_lengths = [5.0, 3.0, 4.0]
        assert compute_spl(successes, path_lengths, optimal_lengths) == 1.0

    def test_all_failure(self):
        successes = [False, False, False]
        path_lengths = [5.0, 3.0, 4.0]
        optimal_lengths = [5.0, 3.0, 4.0]
        assert compute_spl(successes, path_lengths, optimal_lengths) == 0.0

    def test_mixed_results(self):
        successes = [True, False, True]
        path_lengths = [10.0, 5.0, 8.0]
        optimal_lengths = [5.0, 5.0, 4.0]
        spl = compute_spl(successes, path_lengths, optimal_lengths)
        expected = (1 / 3) * (5.0 / 10.0 + 0.0 + 4.0 / 8.0)
        assert abs(spl - expected) < 1e-6

    def test_zero_distances(self):
        successes = [True]
        path_lengths = [0.0]
        optimal_lengths = [0.0]
        assert compute_spl(successes, path_lengths, optimal_lengths) == 0.0


class TestComputeSuccessRate:
    def test_empty(self):
        assert compute_success_rate([]) == 0.0

    def test_all_success(self):
        assert compute_success_rate([True, True, True]) == 1.0

    def test_all_failure(self):
        assert compute_success_rate([False, False]) == 0.0

    def test_mixed(self):
        assert compute_success_rate([True, False, True, False]) == 0.5


class TestComputeCoverage:
    def test_zero_total(self):
        assert compute_coverage(50, 0) == 0.0

    def test_full_coverage(self):
        assert compute_coverage(100, 100) == 1.0

    def test_partial_coverage(self):
        assert abs(compute_coverage(75, 100) - 0.75) < 1e-6


class TestEpisodeResult:
    def test_construction(self):
        ep = EpisodeResult(
            episode_id=0,
            success=True,
            duration=5.0,
            path_length=3.2,
            optimal_length=3.0,
            reason="reached",
        )
        assert ep.success is True
        assert ep.duration == 5.0


class TestBenchmarkReport:
    def test_to_json(self):
        report = BenchmarkReport(
            task="pointnav",
            backend="gazebo",
            num_episodes=10,
            success_rate=0.8,
            spl=0.75,
            avg_duration=5.0,
            avg_path_length=3.5,
            timestamp="2024-01-01T00:00:00",
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["task"] == "pointnav"
        assert parsed["success_rate"] == 0.8
        assert parsed["spl"] == 0.75

    def test_save(self, tmp_path):
        report = BenchmarkReport(
            task="exploration",
            backend="gazebo",
            num_episodes=5,
            success_rate=0.6,
            spl=0.5,
            avg_duration=10.0,
            avg_path_length=2.0,
            coverage=0.7,
            timestamp="2024-01-01T12:00:00",
        )
        path = tmp_path / "reports" / "test_report.json"
        report.save(path)

        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["coverage"] == 0.7
        assert loaded["num_episodes"] == 5


class TestBenchmarkRunner:
    def test_build_report(self):
        runner = BenchmarkRunner(backend="gazebo")
        episodes = [
            EpisodeResult(
                episode_id=0, success=True, duration=3.0, path_length=4.0, optimal_length=3.5
            ),
            EpisodeResult(
                episode_id=1, success=False, duration=5.0, path_length=6.0, optimal_length=4.0
            ),
            EpisodeResult(
                episode_id=2, success=True, duration=4.0, path_length=5.0, optimal_length=4.5
            ),
        ]
        report = runner._build_report("pointnav", episodes)

        assert report.task == "pointnav"
        assert report.backend == "gazebo"
        assert report.num_episodes == 3
        assert abs(report.success_rate - 2 / 3) < 1e-6
        assert report.spl > 0
        assert abs(report.avg_duration - 4.0) < 1e-6
