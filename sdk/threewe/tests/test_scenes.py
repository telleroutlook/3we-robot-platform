# SPDX-License-Identifier: Apache-2.0
"""Tests for the scenes registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from threewe.scenes import SceneMetadata, list_scenes, load_scene
from threewe.scenes.registry import Pose2D


class TestListScenes:
    def test_returns_all_builtin(self):
        scenes = list_scenes()
        assert "office_v2" in scenes
        assert "apartment_v1" in scenes
        assert "corridor_v1" in scenes
        assert "warehouse_v1" in scenes
        assert "cluttered_v1" in scenes
        assert "outdoor_v1" in scenes
        assert "dynamic_v1" in scenes
        assert len(scenes) == 7

    def test_returns_list_of_strings(self):
        scenes = list_scenes()
        assert all(isinstance(s, str) for s in scenes)

    def test_filter_by_tag_indoor(self):
        scenes = list_scenes(tag="indoor")
        assert "office_v2" in scenes
        assert "apartment_v1" in scenes
        assert "outdoor_v1" not in scenes

    def test_filter_by_tag_outdoor(self):
        scenes = list_scenes(tag="outdoor")
        assert "outdoor_v1" in scenes
        assert "office_v2" not in scenes

    def test_filter_by_tag_dynamic(self):
        scenes = list_scenes(tag="dynamic")
        assert "dynamic_v1" in scenes
        assert len(scenes) == 1

    def test_filter_by_nonexistent_tag(self):
        scenes = list_scenes(tag="nonexistent")
        assert scenes == []


class TestLoadScene:
    def test_load_office_v2(self):
        scene = load_scene("office_v2")
        assert isinstance(scene, SceneMetadata)
        assert scene.name == "office_v2"
        assert scene.area == "20x15m"
        assert scene.difficulty == "simple"
        assert len(scene.start_poses) == 20
        assert len(scene.goal_poses) == 50

    def test_load_apartment_v1(self):
        scene = load_scene("apartment_v1")
        assert scene.name == "apartment_v1"
        assert scene.area == "8x10m"
        assert scene.difficulty == "medium"
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 30

    def test_load_corridor_v1(self):
        scene = load_scene("corridor_v1")
        assert scene.name == "corridor_v1"
        assert scene.area == "50m linear"
        assert scene.difficulty == "simple"
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 25

    def test_load_warehouse_v1(self):
        scene = load_scene("warehouse_v1")
        assert scene.name == "warehouse_v1"
        assert scene.area == "40x30m"
        assert scene.difficulty == "medium"
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 40

    def test_load_cluttered_v1(self):
        scene = load_scene("cluttered_v1")
        assert scene.name == "cluttered_v1"
        assert scene.difficulty == "hard"
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 30

    def test_load_outdoor_v1(self):
        scene = load_scene("outdoor_v1")
        assert scene.name == "outdoor_v1"
        assert scene.area == "50x50m"
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 35

    def test_load_dynamic_v1(self):
        scene = load_scene("dynamic_v1")
        assert scene.name == "dynamic_v1"
        assert scene.dynamic_obstacles is True
        assert "dynamic" in scene.tags
        assert len(scene.start_poses) == 15
        assert len(scene.goal_poses) == 30

    def test_scene_tags_field(self):
        scene = load_scene("office_v2")
        assert isinstance(scene.tags, tuple)
        assert "indoor" in scene.tags

    def test_dynamic_obstacles_default_false(self):
        scene = load_scene("office_v2")
        assert scene.dynamic_obstacles is False

    def test_poses_are_pose2d(self):
        scene = load_scene("office_v2")
        for pose in scene.start_poses:
            assert isinstance(pose, Pose2D)
            assert isinstance(pose.x, float)
            assert isinstance(pose.y, float)
            assert isinstance(pose.theta, float)

    def test_scene_is_frozen(self):
        scene = load_scene("office_v2")
        with pytest.raises(AttributeError):
            scene.name = "modified"  # type: ignore[misc]

    def test_unknown_scene_raises(self):
        with pytest.raises(ValueError, match="Unknown scene"):
            load_scene("nonexistent_scene")

    def test_load_from_directory(self, tmp_path: Path):
        yaml = pytest.importorskip("yaml")

        meta = {"name": "custom", "area": "5x5m", "difficulty": "hard", "description": "Test scene"}
        starts = {"poses": [{"x": 1.0, "y": 2.0, "theta": 0.5}]}
        goals = {"poses": [{"x": 3.0, "y": 4.0}]}

        (tmp_path / "metadata.yaml").write_text(yaml.dump(meta))
        (tmp_path / "start_poses.yaml").write_text(yaml.dump(starts))
        (tmp_path / "goal_poses.yaml").write_text(yaml.dump(goals))

        scene = load_scene(str(tmp_path))
        assert scene.name == "custom"
        assert scene.difficulty == "hard"
        assert len(scene.start_poses) == 1
        assert scene.start_poses[0].x == 1.0
        assert scene.start_poses[0].theta == 0.5
        assert len(scene.goal_poses) == 1
        assert scene.goal_poses[0].theta == 0.0

    def test_missing_file_raises(self, tmp_path: Path):
        yaml = pytest.importorskip("yaml")

        meta = {
            "name": "incomplete",
            "area": "1x1m",
            "difficulty": "simple",
            "description": "Missing files",
        }
        (tmp_path / "metadata.yaml").write_text(yaml.dump(meta))

        with pytest.raises(FileNotFoundError):
            load_scene(str(tmp_path))


class TestPose2D:
    def test_default_theta(self):
        pose = Pose2D(x=1.0, y=2.0)
        assert pose.theta == 0.0

    def test_frozen(self):
        pose = Pose2D(x=1.0, y=2.0, theta=0.5)
        with pytest.raises(AttributeError):
            pose.x = 3.0  # type: ignore[misc]
