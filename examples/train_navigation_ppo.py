# SPDX-License-Identifier: Apache-2.0
"""Train a PPO navigation policy using stable-baselines3 and the threewe gymnasium env.

This script trains a PPO agent to navigate point-to-point in the 3we/Navigation-v1
environment, evaluates the trained policy, saves the model, and demonstrates how to
deploy the trained policy on a real robot.

Requirements:
    pip install threewe[sim] stable-baselines3

Usage:
    python examples/train_navigation_ppo.py
    python examples/train_navigation_ppo.py --timesteps 500000 --save-path models/nav_ppo
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

import threewe.gym  # noqa: F401 — registers 3we environments

try:
    import gymnasium
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
except ImportError as e:
    raise ImportError(
        "This example requires gymnasium and stable-baselines3. "
        "Install with: pip install threewe[sim] stable-baselines3"
    ) from e


def make_env(max_steps: int = 500, arena_size: float = 5.0):
    """Factory function for creating the navigation environment."""

    def _init():
        return gymnasium.make(
            "3we/Navigation-v1",
            max_steps=max_steps,
            arena_size=arena_size,
        )

    return _init


def train(timesteps: int, save_path: str) -> PPO:
    """Train a PPO agent on the navigation task.

    Args:
        timesteps: Total training timesteps.
        save_path: Path to save the trained model.

    Returns:
        The trained PPO model.
    """
    env = VecMonitor(DummyVecEnv([make_env()]))

    model = PPO(
        policy="MultiInputPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
    )

    print(f"Training PPO for {timesteps:,} timesteps...")
    model.learn(total_timesteps=timesteps)

    model.save(save_path)
    print(f"Model saved to: {save_path}")

    env.close()
    return model


def evaluate(model: PPO, num_episodes: int = 10) -> float:
    """Evaluate the trained policy.

    Args:
        model: Trained PPO model.
        num_episodes: Number of evaluation episodes.

    Returns:
        Success rate (fraction of episodes where goal was reached).
    """
    env = DummyVecEnv([make_env()])
    successes = 0

    for episode in range(num_episodes):
        obs = env.reset()
        done = False
        episode_reward = 0.0

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            episode_reward += reward[0]

        final_distance = info[0].get("distance", float("inf"))
        if final_distance < 0.2:
            successes += 1

        print(
            f"  Episode {episode + 1}/{num_episodes}: reward={episode_reward:.1f}, "
            f"distance={final_distance:.3f}"
        )

    env.close()

    success_rate = successes / num_episodes
    print(
        f"\nEvaluation complete: {successes}/{num_episodes} successes (SR={success_rate:.2f})"
    )
    return success_rate


def deploy_on_real_robot(model_path: str) -> None:
    """Demonstrate deploying the trained policy on a real robot.

    This function shows the deployment pattern. It requires a physical robot
    or running simulation to actually execute.

    Args:
        model_path: Path to the saved PPO model.
    """
    import asyncio

    from threewe import Robot

    loaded_model = PPO.load(model_path)

    async def run_policy():
        async with Robot(backend="real") as robot:
            print("Connected to real robot. Running learned policy...")

            # Get observation in the same format the policy expects
            obs = robot.get_observation(
                modalities=["image", "lidar", "pose", "velocity"]
            )

            # Add goal information (in practice, this would come from a task planner)
            goal = np.array([2.0, 1.5], dtype=np.float32)
            obs["goal"] = goal

            for step in range(200):
                # Policy predicts normalized action [-1, 1]
                action, _ = loaded_model.predict(obs, deterministic=True)

                # Execute on robot (threewe handles scaling to real velocities)
                robot.execute_action(action)

                # Get next observation
                obs = robot.get_observation(
                    modalities=["image", "lidar", "pose", "velocity"]
                )
                obs["goal"] = goal

                # Check if goal reached
                pose = robot.get_pose()
                dx = goal[0] - pose.x
                dy = goal[1] - pose.y
                distance = np.sqrt(dx * dx + dy * dy)

                if distance < 0.2:
                    print(f"Goal reached in {step + 1} steps!")
                    break

            robot.stop()

    asyncio.run(run_policy())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a PPO navigation policy on the 3we platform"
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=100_000,
        help="Total training timesteps (default: 100000)",
    )
    parser.add_argument(
        "--save-path",
        type=str,
        default="models/navigation_ppo",
        help="Path to save the trained model (default: models/navigation_ppo)",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=10,
        help="Number of evaluation episodes (default: 10)",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Run deployment demo on real robot after training",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Train
    model = train(timesteps=args.timesteps, save_path=args.save_path)

    # Evaluate
    success_rate = evaluate(model, num_episodes=args.eval_episodes)

    if success_rate < 0.5:
        print("\nWarning: Low success rate. Consider training for more timesteps.")

    # Optional: deploy on real robot
    if args.deploy:
        print("\n--- Deploying on real robot ---")
        deploy_on_real_robot(args.save_path)
    else:
        print(
            "\nTo deploy on a real robot, run with --deploy flag "
            "or call deploy_on_real_robot() programmatically."
        )

    sys.exit(0)
