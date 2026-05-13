# SPDX-License-Identifier: Apache-2.0
"""Tests for the ObjectNav benchmark runner and get_observation()."""

from __future__ import annotations

import pytest

from threewe.benchmark.baselines import BASELINES, compare_to_baseline
from threewe.benchmark.objectnav_runner import (
    ObjectNavEpisodeConfig,
    generate_objectnav_episodes,
)
from threewe.benchmark.runner import BenchmarkRunner, EpisodeResult
from threewe.benchmark.tasks import ObjectNavTask
from threewe.types import Pose2D


class TestObjectNavEpisodeConfig:
    def test_creation(self):
        config = ObjectNavEpisodeConfig(
            target_category="chair",
            target_position=Pose2D(x=3.0, y=2.0, theta=0.0),
            start_pose=Pose2D(x=0.0, y=0.0, theta=0.0),
        )
        assert config.target_category == "chair"
        assert config.target_position.x == 3.0
        assert config.success_radius == 1.0
        assert config.timeout == 60.0

    def test_custom_radius_and_timeout(self):
        config = ObjectNavEpisodeConfig(
            target_category="desk",
            target_position=Pose2D(x=5.0, y=1.0),
            start_pose=Pose2D(x=0.0, y=0.0),
            success_radius=2.0,
            timeout=120.0,
        )
        assert config.success_radius == 2.0
        assert config.timeout == 120.0

    def test_frozen(self):
        config = ObjectNavEpisodeConfig(
            target_category="chair",
            target_position=Pose2D(x=1.0, y=1.0),
            start_pose=Pose2D(x=0.0, y=0.0),
        )
        with pytest.raises(AttributeError):
            config.target_category = "desk"  # type: ignore[misc]


class TestGenerateObjectNavEpisodes:
    def test_generates_correct_count(self):
        episodes = generate_objectnav_episodes("office_v2", num_episodes=10, seed=42)
        assert len(episodes) == 10

    def test_deterministic_with_seed(self):
        ep1 = generate_objectnav_episodes("office_v2", num_episodes=5, seed=123)
        ep2 = generate_objectnav_episodes("office_v2", num_episodes=5, seed=123)
        for a, b in zip(ep1, ep2, strict=True):
            assert a.target_category == b.target_category
            assert a.target_position == b.target_position
            assert a.start_pose == b.start_pose

    def test_different_seeds_differ(self):
        ep1 = generate_objectnav_episodes("office_v2", num_episodes=20, seed=1)
        ep2 = generate_objectnav_episodes("office_v2", num_episodes=20, seed=2)
        categories1 = [e.target_category for e in ep1]
        categories2 = [e.target_category for e in ep2]
        assert categories1 != categories2

    def test_uses_valid_object_categories(self):
        task = ObjectNavTask()
        episodes = generate_objectnav_episodes("office_v2", num_episodes=50, seed=0)
        for ep in episodes:
            assert ep.target_category in task.object_categories

    def test_apartment_scene(self):
        episodes = generate_objectnav_episodes("apartment_v1", num_episodes=5, seed=0)
        assert len(episodes) == 5


class TestObjectNavBaselines:
    def test_objectnav_office_baseline_exists(self):
        assert "nav2_objectnav_office" in BASELINES
        b = BASELINES["nav2_objectnav_office"]
        assert b.task == "objectnav"
        assert b.scene == "office_v2"
        assert 0 < b.success_rate < 1

    def test_objectnav_apartment_baseline_exists(self):
        assert "nav2_objectnav_apartment" in BASELINES
        b = BASELINES["nav2_objectnav_apartment"]
        assert b.task == "objectnav"
        assert b.scene == "apartment_v1"
        assert 0 < b.success_rate < 1

    def test_compare_objectnav_baseline(self):
        result = compare_to_baseline(
            baseline_name="nav2_objectnav_office",
            success_rate=0.60,
            spl=0.42,
            avg_duration=20.0,
        )
        assert result.success_rate_delta == pytest.approx(0.05, abs=0.01)
        assert result.spl_delta == pytest.approx(0.04, abs=0.01)
        assert result.improved is True


class TestObjectNavTask:
    def test_task_valid_scenes(self):
        task = ObjectNavTask()
        assert "office_v2" in task.valid_scenes
        assert "apartment_v1" in task.valid_scenes

    def test_task_object_categories(self):
        task = ObjectNavTask()
        assert len(task.object_categories) >= 5
        assert "chair" in task.object_categories
        assert "desk" in task.object_categories

    def test_is_success(self):
        task = ObjectNavTask()
        ep = EpisodeResult(episode_id=0, success=True, duration=10.0, path_length=5.0)
        assert task.is_success(ep) is True

        ep_fail = EpisodeResult(episode_id=1, success=False, duration=60.0, path_length=0.0)
        assert task.is_success(ep_fail) is False


class TestBenchmarkRunnerObjectNav:
    def test_runner_has_objectnav_method(self):
        runner = BenchmarkRunner(backend="gazebo", scene="office_v2")
        assert hasattr(runner, "run_objectnav")


class TestGetObservation:
    def test_default_modalities(self):
        from threewe import Robot

        robot = Robot(backend="gazebo", auto_connect=False)
        # Can't call get_observation without connection, but verify method signature
        import inspect

        sig = inspect.signature(robot.get_observation)
        params = list(sig.parameters.keys())
        assert "modalities" in params

    def test_default_modalities_tuple(self):
        from threewe import Robot

        robot = Robot(backend="gazebo", auto_connect=False)
        assert "image" in robot._DEFAULT_MODALITIES
        assert "lidar" in robot._DEFAULT_MODALITIES
        assert "pose" in robot._DEFAULT_MODALITIES
        assert "velocity" in robot._DEFAULT_MODALITIES

    def test_invalid_modality_raises(self):
        from unittest.mock import patch

        from threewe import Robot

        robot = Robot(backend="gazebo", auto_connect=False)
        # Mock the connection check to pass
        with patch.object(robot, "_ensure_connected"):
            with pytest.raises(ValueError, match="Unknown modality"):
                robot.get_observation(modalities=["nonexistent"])

    def test_selective_modalities(self):
        from unittest.mock import patch

        from threewe import Robot
        from threewe.types import Pose2D as P2D

        robot = Robot(backend="gazebo", auto_connect=False)

        mock_pose = P2D(x=1.0, y=2.0, theta=0.5)
        with (
            patch.object(robot, "_ensure_connected"),
            patch.object(robot, "get_pose", return_value=mock_pose),
        ):
            obs = robot.get_observation(modalities=["pose"])
            assert "pose" in obs
            assert "image" not in obs
            assert obs["pose"][0] == pytest.approx(1.0)
            assert obs["pose"][1] == pytest.approx(2.0)
            assert obs["pose"][2] == pytest.approx(0.5)
