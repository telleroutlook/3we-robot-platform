# SPDX-License-Identifier: Apache-2.0
"""Tests for benchmark tasks and baselines."""

from __future__ import annotations

import pytest

from threewe.benchmark.baselines import (
    BASELINES,
    BaselineResult,
    compare_to_baseline,
    list_baselines,
)
from threewe.benchmark.runner import EpisodeResult
from threewe.benchmark.tasks import (
    ExplorationTask,
    ObjectNavTask,
    PointNavTask,
    get_task,
    list_tasks,
)


class TestBenchmarkTasks:
    def test_list_tasks(self):
        tasks = list_tasks()
        assert "pointnav" in tasks
        assert "objectnav" in tasks
        assert "exploration" in tasks
        assert len(tasks) == 3

    def test_get_task_pointnav(self):
        task = get_task("pointnav")
        assert task.name == "pointnav"
        assert "spl" in task.metrics
        assert "success_rate" in task.metrics

    def test_get_task_objectnav(self):
        task = get_task("objectnav")
        assert task.name == "objectnav"
        assert "office_v2" in task.valid_scenes

    def test_get_task_exploration(self):
        task = get_task("exploration")
        assert task.name == "exploration"
        assert "coverage" in task.metrics

    def test_get_unknown_task_raises(self):
        with pytest.raises(ValueError, match="Unknown task"):
            get_task("nonexistent")

    def test_pointnav_is_success(self):
        task = PointNavTask()
        ep_success = EpisodeResult(episode_id=0, success=True, duration=5.0, path_length=3.0)
        ep_fail = EpisodeResult(episode_id=1, success=False, duration=30.0, path_length=0.0)
        assert task.is_success(ep_success) is True
        assert task.is_success(ep_fail) is False

    def test_objectnav_categories(self):
        task = ObjectNavTask()
        assert len(task.object_categories) == 10
        assert "chair" in task.object_categories

    def test_exploration_coverage_threshold(self):
        task = ExplorationTask()
        ep_good = EpisodeResult(
            episode_id=0, success=True, duration=90.0, path_length=0.0, coverage=0.85
        )
        ep_bad = EpisodeResult(
            episode_id=1, success=False, duration=120.0, path_length=0.0, coverage=0.5
        )
        assert task.is_success(ep_good) is True
        assert task.is_success(ep_bad) is False

    def test_tasks_are_frozen(self):
        task = PointNavTask()
        with pytest.raises(AttributeError):
            task.name = "modified"  # type: ignore[misc]


class TestBaselines:
    def test_list_baselines(self):
        baselines = list_baselines()
        assert "nav2_pointnav_office" in baselines
        assert "frontier_exploration_corridor" in baselines
        assert len(baselines) == 5

    def test_baseline_structure(self):
        baseline = BASELINES["nav2_pointnav_office"]
        assert isinstance(baseline, BaselineResult)
        assert baseline.task == "pointnav"
        assert baseline.scene == "office_v2"
        assert 0.0 <= baseline.success_rate <= 1.0
        assert baseline.spl >= 0.0

    def test_compare_improved(self):
        result = compare_to_baseline(
            baseline_name="nav2_pointnav_office",
            success_rate=0.90,
            spl=0.70,
            avg_duration=10.0,
        )
        assert result.improved is True
        assert result.success_rate_delta > 0
        assert result.spl_delta > 0

    def test_compare_regressed(self):
        result = compare_to_baseline(
            baseline_name="nav2_pointnav_office",
            success_rate=0.50,
            spl=0.30,
            avg_duration=20.0,
        )
        assert result.improved is False
        assert result.success_rate_delta < 0

    def test_compare_unknown_baseline_raises(self):
        with pytest.raises(ValueError, match="Unknown baseline"):
            compare_to_baseline(
                baseline_name="nonexistent",
                success_rate=0.9,
                spl=0.7,
                avg_duration=10.0,
            )

    def test_baselines_are_frozen(self):
        baseline = BASELINES["nav2_pointnav_office"]
        with pytest.raises(AttributeError):
            baseline.success_rate = 1.0  # type: ignore[misc]
