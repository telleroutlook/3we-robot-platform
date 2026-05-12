# SPDX-License-Identifier: Apache-2.0
"""RL Obstacle Avoidance — Train a PPO agent in simulation.

Usage:
    pip install threewe[sim] stable-baselines3
    python examples/rl_obstacle_avoidance.py
"""

import threewe.gym  # noqa: F401 — registers environments

try:
    import gymnasium
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
except ImportError as e:
    raise ImportError("This example requires: pip install threewe[sim] stable-baselines3") from e


def make_env():
    return gymnasium.make("3we/Navigation-v1", max_steps=200, arena_size=3.0)


def main():
    env = DummyVecEnv([make_env])

    model = PPO(
        "MultiInputPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
    )

    print("Training PPO agent for obstacle avoidance...")
    model.learn(total_timesteps=50_000)

    print("Training complete. Evaluating...")
    obs = env.reset()
    total_reward = 0.0
    for _ in range(200):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        total_reward += reward[0]
        if done[0]:
            break

    print(f"Evaluation reward: {total_reward:.1f}")
    env.close()


if __name__ == "__main__":
    main()
