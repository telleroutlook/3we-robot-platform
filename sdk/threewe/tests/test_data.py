# SPDX-License-Identifier: Apache-2.0
"""Tests for TrajectoryRecorder and data export."""

from __future__ import annotations

import numpy as np
import pytest

from threewe.data.recorder import Episode, TimeStep, TrajectoryRecorder


class TestTimeStep:
    def test_construction(self):
        step = TimeStep(
            timestamp=1.0,
            image=np.zeros((64, 64, 3), dtype=np.uint8),
            pose=np.array([1.0, 2.0, 0.5], dtype=np.float32),
            velocity=np.array([0.1, 0.0, 0.0], dtype=np.float32),
            action=np.array([0.2, 0.0, 0.1], dtype=np.float32),
        )
        assert step.timestamp == 1.0
        assert step.lidar is None
        assert step.depth is None


class TestEpisode:
    def test_empty_episode(self):
        ep = Episode()
        assert ep.length == 0
        assert ep.duration == 0.0

    def test_episode_duration(self):
        steps = [
            TimeStep(
                timestamp=float(i),
                image=np.zeros((4, 4, 3), dtype=np.uint8),
                pose=np.zeros(3, dtype=np.float32),
                velocity=np.zeros(3, dtype=np.float32),
                action=np.zeros(3, dtype=np.float32),
            )
            for i in range(5)
        ]
        ep = Episode(steps=steps)
        assert ep.length == 5
        assert ep.duration == 4.0


class TestTrajectoryRecorder:
    def test_start_and_end_episode(self, connected_robot):
        recorder = TrajectoryRecorder(connected_robot)
        assert recorder.num_episodes == 0

        recorder.start_episode(metadata={"task": "test"})
        recorder.record_step(action=[0.1, 0.0, 0.0])
        recorder.record_step(action=[0.2, 0.0, 0.1])
        ep = recorder.end_episode()

        assert recorder.num_episodes == 1
        assert recorder.total_steps == 2
        assert ep.length == 2
        assert ep.metadata["task"] == "test"

    def test_record_step_without_episode_raises(self, connected_robot):
        recorder = TrajectoryRecorder(connected_robot)
        with pytest.raises(RuntimeError, match="Call start_episode"):
            recorder.record_step(action=[0.0, 0.0, 0.0])

    def test_end_episode_without_start_raises(self, connected_robot):
        recorder = TrajectoryRecorder(connected_robot)
        with pytest.raises(RuntimeError, match="No episode in progress"):
            recorder.end_episode()

    def test_multiple_episodes(self, connected_robot):
        recorder = TrajectoryRecorder(connected_robot)

        recorder.start_episode()
        recorder.record_step(action=[0.1, 0.0, 0.0])
        recorder.end_episode()

        recorder.start_episode()
        recorder.record_step(action=[0.2, 0.0, 0.0])
        recorder.record_step(action=[0.3, 0.0, 0.0])
        recorder.end_episode()

        assert recorder.num_episodes == 2
        assert recorder.total_steps == 3

    def test_save_hdf5(self, connected_robot, tmp_path):
        h5py = pytest.importorskip("h5py")

        recorder = TrajectoryRecorder(connected_robot)
        recorder.start_episode(metadata={"scene": "office"})
        for _ in range(3):
            recorder.record_step(action=[0.1, 0.0, 0.05])
        recorder.end_episode()

        path = tmp_path / "test_traj.h5"
        recorder.save_hdf5(path)

        assert path.exists()
        with h5py.File(path, "r") as f:
            assert f.attrs["num_episodes"] == 1
            assert f.attrs["total_steps"] == 3
            assert "episode_000" in f
            grp = f["episode_000"]
            assert grp.attrs["length"] == 3
            assert grp["images"].shape == (3, 480, 640, 3)
            assert grp["poses"].shape == (3, 3)
            assert grp["actions"].shape == (3, 3)
            assert grp["timestamps"].shape == (3,)

    def test_save_lerobot(self, connected_robot, tmp_path):
        recorder = TrajectoryRecorder(connected_robot)
        recorder.start_episode()
        recorder.record_step(action=[0.1, 0.0, 0.0])
        recorder.record_step(action=[0.2, 0.0, 0.0])
        recorder.end_episode()

        output_dir = tmp_path / "lerobot_export"
        recorder.save_lerobot(output_dir)

        assert (output_dir / "meta" / "info.json").exists()
        assert (output_dir / "data").exists()

    def test_record_with_lidar(self, connected_robot):
        recorder = TrajectoryRecorder(connected_robot, record_lidar=True)
        recorder.start_episode()
        recorder.record_step(action=[0.1, 0.0, 0.0])
        ep = recorder.end_episode()

        assert ep.steps[0].lidar is not None
        assert ep.steps[0].lidar.shape == (360,)
