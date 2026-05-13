# SPDX-License-Identifier: Apache-2.0
"""Data Collection — Record trajectories for imitation learning.

Demonstrates:
  - Using TrajectoryRecorder to capture observation-action pairs
  - Recording multiple episodes with metadata
  - Saving to HDF5 format (for PyTorch/NumPy consumption)
  - Exporting to LeRobot-compatible format (Parquet + MP4)

Usage:
    python examples/data_collection.py
    python examples/data_collection.py --episodes 5 --steps 50
    python examples/data_collection.py --backend real --record-lidar
"""

import argparse
import asyncio

import numpy as np

from threewe import Robot
from threewe.data.recorder import TrajectoryRecorder


async def collect_random_walk_episode(
    robot: Robot,
    recorder: TrajectoryRecorder,
    num_steps: int,
    episode_id: int,
) -> None:
    """Collect one episode of random-walk exploration."""
    recorder.start_episode(
        metadata={
            "task": "random_exploration",
            "episode_id": episode_id,
            "scene": robot.backend_name,
        }
    )

    for _step in range(num_steps):
        vx = np.random.uniform(0.0, 0.3)
        vy = np.random.uniform(-0.1, 0.1)
        omega = np.random.uniform(-0.5, 0.5)

        robot.set_velocity(vx, vy, omega)
        await asyncio.sleep(0.1)

        recorder.record_step(action=[vx, vy, omega])

    robot.stop()
    episode = recorder.end_episode()
    print(f"  Episode {episode_id}: {episode.length} steps, {episode.duration:.1f}s")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Collect robot trajectories for IL")
    parser.add_argument(
        "--backend", default="mock", choices=["mock", "gazebo", "real", "isaac_sim"]
    )
    parser.add_argument("--episodes", type=int, default=3, help="Number of episodes to record")
    parser.add_argument("--steps", type=int, default=30, help="Steps per episode")
    parser.add_argument("--output", default="data/trajectories.h5", help="HDF5 output path")
    parser.add_argument("--lerobot-dir", default="data/lerobot_export", help="LeRobot export dir")
    parser.add_argument("--record-lidar", action="store_true", help="Also record LiDAR scans")
    parser.add_argument("--record-depth", action="store_true", help="Also record depth images")
    args = parser.parse_args()

    async with Robot(backend=args.backend) as robot:
        recorder = TrajectoryRecorder(
            robot,
            record_lidar=args.record_lidar,
            record_depth=args.record_depth,
        )

        print(f"Recording {args.episodes} episodes ({args.steps} steps each)...")
        print(f"  Backend: {args.backend}")
        print(f"  LiDAR: {args.record_lidar}, Depth: {args.record_depth}\n")

        for i in range(args.episodes):
            await collect_random_walk_episode(robot, recorder, args.steps, i)

        print(f"\nTotal: {recorder.num_episodes} episodes, {recorder.total_steps} steps")

        print(f"\nSaving HDF5 → {args.output}")
        recorder.save_hdf5(args.output)

        print(f"Exporting LeRobot format → {args.lerobot_dir}/")
        recorder.save_lerobot(args.lerobot_dir)

        print("\nDone! Files ready for imitation learning training.")


if __name__ == "__main__":
    asyncio.run(main())
