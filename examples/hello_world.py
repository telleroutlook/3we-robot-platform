# SPDX-License-Identifier: Apache-2.0
"""Hello World — Connect to the robot, capture an image, and navigate.

Usage:
    python examples/hello_world.py
"""

import asyncio

from threewe import Robot


async def main():
    async with Robot(backend="gazebo") as robot:
        # Get current pose
        pose = robot.get_pose()
        print(f"Current pose: x={pose.x:.2f}, y={pose.y:.2f}, theta={pose.theta:.2f}")

        # Capture a camera image
        image = robot.get_image()
        print(f"Image shape: {image.shape}")

        # Navigate to a point
        result = await robot.move_to(x=2.0, y=1.0)
        print(f"Navigation: {'success' if result.success else 'failed'} — {result.reason}")

        # Get final pose
        final_pose = robot.get_pose()
        print(f"Final pose: x={final_pose.x:.2f}, y={final_pose.y:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
