# SPDX-License-Identifier: Apache-2.0
"""Trajectory recording for imitation learning data collection.

Records observation-action pairs during teleoperation or autonomous execution,
then exports to HDF5 or LeRobot-compatible formats.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from threewe.robot import Robot


@dataclass
class TimeStep:
    """A single recorded timestep."""

    timestamp: float
    image: np.ndarray
    pose: np.ndarray  # (3,) [x, y, theta]
    velocity: np.ndarray  # (3,) [vx, vy, omega]
    action: np.ndarray  # (3,) [vx_cmd, vy_cmd, omega_cmd]
    lidar: np.ndarray | None = None
    depth: np.ndarray | None = None


@dataclass
class Episode:
    """A single recorded episode (trajectory)."""

    steps: list[TimeStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def duration(self) -> float:
        if len(self.steps) < 2:
            return 0.0
        return self.steps[-1].timestamp - self.steps[0].timestamp


class TrajectoryRecorder:
    """Records robot trajectories for imitation learning.

    Usage:
        recorder = TrajectoryRecorder(robot)
        recorder.start_episode()
        # ... control robot ...
        recorder.record_step(action=[0.1, 0.0, 0.0])
        recorder.end_episode()
        recorder.save_hdf5("trajectories.h5")
    """

    def __init__(
        self,
        robot: Robot,
        record_lidar: bool = False,
        record_depth: bool = False,
    ) -> None:
        self._robot = robot
        self._record_lidar = record_lidar
        self._record_depth = record_depth
        self._episodes: list[Episode] = []
        self._current_episode: Episode | None = None

    @property
    def num_episodes(self) -> int:
        return len(self._episodes)

    @property
    def total_steps(self) -> int:
        return sum(ep.length for ep in self._episodes)

    def start_episode(self, metadata: dict | None = None) -> None:
        """Start recording a new episode."""
        self._current_episode = Episode(metadata=metadata or {})

    def record_step(self, action: list[float] | np.ndarray) -> None:
        """Record current observation and the action taken."""
        if self._current_episode is None:
            raise RuntimeError("Call start_episode() before recording steps.")

        image = self._robot.get_image()
        pose = self._robot.get_pose()
        velocity = self._robot.get_velocity()

        lidar = None
        if self._record_lidar:
            scan = self._robot.get_lidar_scan()
            lidar = scan.ranges

        depth = None
        if self._record_depth:
            rgbd = self._robot.get_rgbd_image()
            depth = rgbd.depth

        step = TimeStep(
            timestamp=time.time(),
            image=image,
            pose=np.array([pose.x, pose.y, pose.theta], dtype=np.float32),
            velocity=np.array([velocity.vx, velocity.vy, velocity.omega], dtype=np.float32),
            action=np.asarray(action, dtype=np.float32),
            lidar=lidar,
            depth=depth,
        )
        self._current_episode.steps.append(step)

    def end_episode(self) -> Episode:
        """End current episode and store it."""
        if self._current_episode is None:
            raise RuntimeError("No episode in progress.")
        episode = self._current_episode
        self._episodes.append(episode)
        self._current_episode = None
        return episode

    def save_hdf5(self, path: str | Path) -> None:
        """Save all episodes to HDF5 format.

        Structure:
            /episode_000/
                images: (T, H, W, 3) uint8
                poses: (T, 3) float32
                velocities: (T, 3) float32
                actions: (T, 3) float32
                timestamps: (T,) float64
                [lidar: (T, N) float32]
                [depth: (T, H, W) float32]
        """
        try:
            import h5py
        except ImportError as e:
            raise ImportError(
                "h5py is required for HDF5 export. Install with: pip install threewe[data]"
            ) from e

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(path, "w") as f:
            f.attrs["num_episodes"] = len(self._episodes)
            f.attrs["total_steps"] = self.total_steps

            for i, episode in enumerate(self._episodes):
                grp = f.create_group(f"episode_{i:03d}")
                grp.attrs["length"] = episode.length
                grp.attrs["duration"] = episode.duration
                for key, value in episode.metadata.items():
                    grp.attrs[key] = value

                if episode.length == 0:
                    continue

                images = np.stack([s.image for s in episode.steps])
                poses = np.stack([s.pose for s in episode.steps])
                velocities = np.stack([s.velocity for s in episode.steps])
                actions = np.stack([s.action for s in episode.steps])
                timestamps = np.array([s.timestamp for s in episode.steps], dtype=np.float64)

                grp.create_dataset("images", data=images, compression="gzip", compression_opts=4)
                grp.create_dataset("poses", data=poses)
                grp.create_dataset("velocities", data=velocities)
                grp.create_dataset("actions", data=actions)
                grp.create_dataset("timestamps", data=timestamps)

                if self._record_lidar and episode.steps[0].lidar is not None:
                    lidar_data = np.stack([s.lidar for s in episode.steps])
                    grp.create_dataset("lidar", data=lidar_data)

                if self._record_depth and episode.steps[0].depth is not None:
                    depth_data = np.stack([s.depth for s in episode.steps])
                    grp.create_dataset(
                        "depth", data=depth_data, compression="gzip", compression_opts=4
                    )

    def save_lerobot(self, output_dir: str | Path) -> None:
        """Export episodes in LeRobot-compatible format (Parquet + MP4).

        Creates:
            output_dir/
                data/
                    episode_000.parquet
                    episode_001.parquet
                    ...
                videos/
                    episode_000.mp4
                    episode_001.mp4
                    ...
                meta/
                    info.json
        """
        import json

        output_dir = Path(output_dir)
        data_dir = output_dir / "data"
        videos_dir = output_dir / "videos"
        meta_dir = output_dir / "meta"

        data_dir.mkdir(parents=True, exist_ok=True)
        videos_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        for i, episode in enumerate(self._episodes):
            if episode.length == 0:
                continue

            self._export_episode_parquet(episode, data_dir / f"episode_{i:03d}.parquet")
            self._export_episode_video(episode, videos_dir / f"episode_{i:03d}.mp4")

        info = {
            "num_episodes": len(self._episodes),
            "total_steps": self.total_steps,
            "fps": 10,
            "observation_keys": ["image", "pose", "velocity"],
            "action_key": "action",
            "action_dim": 3,
        }
        (meta_dir / "info.json").write_text(json.dumps(info, indent=2))

    def _export_episode_parquet(self, episode: Episode, path: Path) -> None:
        """Export a single episode as Parquet."""
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            rows = []
            for step in episode.steps:
                rows.append(
                    {
                        "timestamp": step.timestamp,
                        "pose_x": step.pose[0],
                        "pose_y": step.pose[1],
                        "pose_theta": step.pose[2],
                        "vel_vx": step.velocity[0],
                        "vel_vy": step.velocity[1],
                        "vel_omega": step.velocity[2],
                        "action_vx": step.action[0],
                        "action_vy": step.action[1],
                        "action_omega": step.action[2],
                    }
                )
            import csv

            with open(path.with_suffix(".csv"), "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return

        table = pa.table(
            {
                "timestamp": [s.timestamp for s in episode.steps],
                "pose_x": [float(s.pose[0]) for s in episode.steps],
                "pose_y": [float(s.pose[1]) for s in episode.steps],
                "pose_theta": [float(s.pose[2]) for s in episode.steps],
                "vel_vx": [float(s.velocity[0]) for s in episode.steps],
                "vel_vy": [float(s.velocity[1]) for s in episode.steps],
                "vel_omega": [float(s.velocity[2]) for s in episode.steps],
                "action_vx": [float(s.action[0]) for s in episode.steps],
                "action_vy": [float(s.action[1]) for s in episode.steps],
                "action_omega": [float(s.action[2]) for s in episode.steps],
            }
        )
        pq.write_table(table, path)

    def _export_episode_video(self, episode: Episode, path: Path) -> None:
        """Export episode images as MP4 video."""
        try:
            import cv2

            h, w = episode.steps[0].image.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(path), fourcc, 10.0, (w, h))
            for step in episode.steps:
                writer.write(step.image)
            writer.release()
        except ImportError:
            pass
