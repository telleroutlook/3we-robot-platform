# SPDX-License-Identifier: Apache-2.0
"""LeRobot data pipeline — record, export, push, pull, and deploy.

This script demonstrates the full LeRobot-compatible data pipeline:
1. Connect to robot in simulation (Gazebo backend)
2. Record teleoperation episodes using TrajectoryRecorder
3. Save trajectories to HDF5
4. Export to LeRobot format (Parquet + MP4)
5. Push dataset to HuggingFace Hub
6. Pull dataset back from Hub
7. Load and deploy a VLA model trained on the data

Requirements:
    pip install threewe[data,hub,ai]

Usage:
    python examples/lerobot_pipeline.py --num-episodes 5 --output-dir data/nav_demos
    python examples/lerobot_pipeline.py --hub-repo user/3we-nav-demos --push
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import numpy as np


async def record_episodes(
    num_episodes: int,
    output_dir: Path,
    steps_per_episode: int = 50,
) -> Path:
    """Record demonstration episodes in simulation.

    Uses random actions to simulate teleoperation. In practice, replace the
    random action generation with actual teleoperation inputs (joystick, VR
    controller, or keyboard).

    Args:
        num_episodes: Number of episodes to record.
        output_dir: Directory to save recordings.
        steps_per_episode: Steps per episode.

    Returns:
        Path to the saved HDF5 file.
    """
    from threewe import Robot
    from threewe.data.recorder import TrajectoryRecorder

    hdf5_path = output_dir / "trajectories.h5"
    output_dir.mkdir(parents=True, exist_ok=True)

    async with Robot(backend="gazebo", scene="office_v2") as robot:
        recorder = TrajectoryRecorder(
            robot,
            record_lidar=True,
            record_depth=False,
        )

        print(f"Recording {num_episodes} episodes...")

        for ep in range(num_episodes):
            recorder.start_episode(
                metadata={
                    "episode_id": ep,
                    "task": "navigation_demo",
                    "scene": "office_v2",
                    "timestamp": time.time(),
                }
            )

            for _step in range(steps_per_episode):
                # Simulate teleoperation with smoothed random actions
                # In production, replace with real teleoperation input
                action = np.random.uniform(-0.3, 0.3, size=3).astype(np.float32)
                action[2] *= 0.5  # Reduce angular velocity for smoother demos

                robot.execute_action(action)
                recorder.record_step(action=action)

                # 10 Hz control loop
                await asyncio.sleep(0.1)

            episode = recorder.end_episode()
            print(
                f"  Episode {ep + 1}/{num_episodes}: "
                f"{episode.length} steps, {episode.duration:.1f}s"
            )

            robot.stop()

        # Save as HDF5
        recorder.save_hdf5(hdf5_path)
        print(
            f"\nSaved HDF5: {hdf5_path} "
            f"({recorder.num_episodes} episodes, {recorder.total_steps} steps)"
        )

        # Export to LeRobot format
        lerobot_dir = output_dir / "lerobot"
        recorder.save_lerobot(lerobot_dir)
        print(f"Exported LeRobot format: {lerobot_dir}/")

    return hdf5_path


def push_to_hub(local_dir: Path, repo_id: str, token: str | None = None) -> str:
    """Push the LeRobot dataset to HuggingFace Hub.

    Args:
        local_dir: Local directory containing LeRobot-format data.
        repo_id: HuggingFace repository ID (e.g., 'user/3we-nav-demos').
        token: HuggingFace API token. Uses cached login if None.

    Returns:
        URL of the uploaded dataset.
    """
    from threewe.data.hub import push_dataset

    print(f"Pushing dataset to HuggingFace Hub: {repo_id}")
    url = push_dataset(local_dir=local_dir, repo_id=repo_id, token=token)
    print(f"Dataset available at: {url}")
    return url


def pull_from_hub(repo_id: str, local_dir: Path, token: str | None = None) -> Path:
    """Pull a LeRobot dataset from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repository ID.
        local_dir: Local directory to download into.
        token: HuggingFace API token.

    Returns:
        Path to the downloaded dataset.
    """
    from threewe.data.hub import pull_dataset

    print(f"Pulling dataset from Hub: {repo_id}")
    path = pull_dataset(repo_id=repo_id, local_dir=local_dir, token=token)
    print(f"Dataset downloaded to: {path}")
    return path


async def deploy_vla_model(model_id: str, num_steps: int = 100) -> None:
    """Load a VLA model from Hub and deploy it on the robot.

    This demonstrates the full loop: data collection -> training (external) ->
    deployment. The VLA model takes observations and produces actions directly.

    Args:
        model_id: HuggingFace model ID (e.g., 'lerobot/act_3we_nav').
        num_steps: Number of inference steps to run.
    """
    from threewe import Robot
    from threewe.ai.vla_runner import VLARunner

    # Load pre-trained VLA model from Hub
    print(f"Loading VLA model: {model_id}")
    vla = VLARunner.from_pretrained(model_id)

    async with Robot(backend="gazebo", scene="office_v2") as robot:
        print(f"Running VLA inference for {num_steps} steps...")

        for step in range(num_steps):
            # Get observation dict
            obs = robot.get_observation(modalities=["image", "lidar", "pose", "velocity"])

            # VLA predicts action from observation + optional instruction
            action = vla.predict(obs, instruction="navigate to the door")

            # Execute action on robot
            robot.execute_action(action)

            if step % 20 == 0:
                pose = robot.get_pose()
                print(f"  Step {step}: pose=({pose.x:.2f}, {pose.y:.2f}, {pose.theta:.2f})")

            await asyncio.sleep(0.1)

        robot.stop()
        print("VLA deployment complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LeRobot data pipeline: record, export, push, pull, deploy"
    )
    parser.add_argument(
        "--num-episodes",
        type=int,
        default=5,
        help="Number of episodes to record (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/nav_demos",
        help="Output directory for recordings (default: data/nav_demos)",
    )
    parser.add_argument(
        "--hub-repo",
        type=str,
        default=None,
        help="HuggingFace repo ID for push/pull (e.g., user/3we-nav-demos)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push dataset to HuggingFace Hub (requires --hub-repo)",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull dataset from HuggingFace Hub (requires --hub-repo)",
    )
    parser.add_argument(
        "--deploy-model",
        type=str,
        default=None,
        help="HuggingFace VLA model ID to deploy (e.g., lerobot/act_3we_nav)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="HuggingFace API token (uses cached login if not provided)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    # Step 1-4: Record episodes and export
    await record_episodes(
        num_episodes=args.num_episodes,
        output_dir=output_dir,
    )

    lerobot_dir = output_dir / "lerobot"

    # Step 5: Push to HuggingFace Hub (optional)
    if args.push:
        if not args.hub_repo:
            print("Error: --hub-repo is required for --push", file=sys.stderr)
            sys.exit(1)
        push_to_hub(lerobot_dir, repo_id=args.hub_repo, token=args.token)

    # Step 6: Pull from HuggingFace Hub (optional)
    if args.pull:
        if not args.hub_repo:
            print("Error: --hub-repo is required for --pull", file=sys.stderr)
            sys.exit(1)
        pull_dir = output_dir / "pulled"
        pull_from_hub(repo_id=args.hub_repo, local_dir=pull_dir, token=args.token)

    # Step 7: Deploy VLA model (optional)
    if args.deploy_model:
        await deploy_vla_model(model_id=args.deploy_model)

    print("\nPipeline complete.")


if __name__ == "__main__":
    asyncio.run(main())
