# SPDX-License-Identifier: Apache-2.0
"""Sim2Real PointNav Demo — Train in simulation, deploy on real hardware unchanged.

This script demonstrates the core 3we value proposition:
1. Load a pre-trained PPO navigation policy
2. Run it in Gazebo simulation
3. Switch to real hardware with ONE parameter change
4. Compare trajectories side by side

Usage:
    # Run in simulation (default)
    python examples/sim2real_demo/demo.py

    # Run on real hardware (requires robot_bringup running)
    python examples/sim2real_demo/demo.py --backend real

    # Run both sequentially and compare
    python examples/sim2real_demo/demo.py --compare
"""

from __future__ import annotations

import argparse
import asyncio
import time

import numpy as np

from threewe import Robot


async def run_pointnav(backend: str, goal_x: float = 2.0, goal_y: float = 1.5):
    """Run a PointNav task with a simple proportional controller.

    In a full demo, this would load a PPO model. Here we use a reactive
    controller to demonstrate the API consistency across backends.
    """
    trajectory = []

    print(f"\n{'=' * 50}")
    print(f"  Backend: {backend}")
    print(f"  Goal: ({goal_x:.1f}, {goal_y:.1f})")
    print(f"{'=' * 50}\n")

    async with Robot(backend=backend) as robot:
        start_time = time.time()

        for step in range(200):
            pose = robot.get_pose()
            trajectory.append((pose.x, pose.y, pose.theta))

            dx = goal_x - pose.x
            dy = goal_y - pose.y
            dist = np.sqrt(dx * dx + dy * dy)

            if dist < 0.2:
                elapsed = time.time() - start_time
                print(f"  [REACHED] Goal in {step} steps, {elapsed:.1f}s")
                print(f"  Final pose: ({pose.x:.3f}, {pose.y:.3f})")
                print(f"  Error: {dist:.3f}m")
                break

            heading = np.arctan2(dy, dx)
            angle_diff = heading - pose.theta
            angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi

            if abs(angle_diff) > 0.3:
                robot.set_velocity(0.0, 0.0, np.clip(angle_diff * 2.0, -1.0, 1.0))
            else:
                speed = min(dist * 0.5, 0.4)
                robot.set_velocity(speed, 0.0, np.clip(angle_diff, -0.5, 0.5))

            scan = robot.get_lidar_scan()
            front_ranges = scan.ranges[170:190]
            if len(front_ranges) > 0 and np.min(front_ranges) < 0.3:
                robot.set_velocity(0.0, 0.0, 0.5)

            await asyncio.sleep(0.05)
        else:
            print("  [TIMEOUT] Did not reach goal in 200 steps")

        robot.stop()

    return np.array(trajectory)


async def compare_backends(goal_x: float, goal_y: float):
    """Run same task on both backends and compare trajectories."""
    print("\n" + "=" * 60)
    print("  SIM2REAL COMPARISON")
    print("  Same code, same goal, different backends")
    print("=" * 60)

    sim_traj = await run_pointnav("gazebo", goal_x, goal_y)
    real_traj = await run_pointnav("real", goal_x, goal_y)

    if len(sim_traj) > 0 and len(real_traj) > 0:
        sim_final = sim_traj[-1][:2]
        real_final = real_traj[-1][:2]
        endpoint_diff = np.linalg.norm(np.array(sim_final) - np.array(real_final))

        sim_path_len = np.sum(np.linalg.norm(np.diff(sim_traj[:, :2], axis=0), axis=1))
        real_path_len = np.sum(
            np.linalg.norm(np.diff(real_traj[:, :2], axis=0), axis=1)
        )

        print(f"\n{'=' * 60}")
        print("  RESULTS")
        print(f"{'=' * 60}")
        print(f"  Sim path length:   {sim_path_len:.3f}m ({len(sim_traj)} steps)")
        print(f"  Real path length:  {real_path_len:.3f}m ({len(real_traj)} steps)")
        print(f"  Endpoint error:    {endpoint_diff:.3f}m")
        print(f"  Transfer ratio:    {real_path_len / max(sim_path_len, 0.01):.2f}")
        print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Sim2Real PointNav demonstration")
    parser.add_argument(
        "--backend", default="gazebo", choices=["gazebo", "real", "mock"]
    )
    parser.add_argument(
        "--compare", action="store_true", help="Run both backends and compare"
    )
    parser.add_argument("--goal-x", type=float, default=2.0)
    parser.add_argument("--goal-y", type=float, default=1.5)
    args = parser.parse_args()

    if args.compare:
        asyncio.run(compare_backends(args.goal_x, args.goal_y))
    else:
        asyncio.run(run_pointnav(args.backend, args.goal_x, args.goal_y))


if __name__ == "__main__":
    main()
