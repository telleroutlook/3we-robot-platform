# SPDX-License-Identifier: Apache-2.0
"""SLAM Exploration — Autonomously explore and build a map.

Usage:
    python examples/slam_exploration.py
"""

import asyncio

from threewe import Robot


async def main():
    async with Robot(backend="gazebo") as robot:
        print("Starting autonomous exploration...")

        # Explore for 60 seconds
        result = await robot.explore(timeout=60.0)

        print("Exploration complete:")
        print(f"  Coverage: {result.coverage * 100:.1f}%")
        print(f"  Duration: {result.duration:.1f}s")
        print(f"  Cells explored: {result.cells_explored}")
        print(f"  Timed out: {result.timed_out}")

        # Get the built map
        grid = robot.get_map()
        print(f"  Map size: {grid.data.shape}")
        print(f"  Resolution: {grid.resolution}m/cell")


if __name__ == "__main__":
    asyncio.run(main())
