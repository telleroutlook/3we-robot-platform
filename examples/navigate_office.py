# SPDX-License-Identifier: Apache-2.0
"""Office navigation demo — showcases the mock backend with real-time status output.

Usage:
    cd sdk/threewe && pip install -e .
    python examples/navigate_office.py
"""

import asyncio

from threewe import Robot
from threewe.types import Pose2D


async def main():
    print("=" * 60)
    print("  3we Robot Platform — Office Navigation Demo")
    print("=" * 60)
    print()

    async with Robot(backend="mock", verbose=True) as robot:
        # Show initial state
        pose = robot.get_pose()
        scan = robot.get_lidar_scan()
        print(f"\n  Start pose: ({pose.x:.1f}, {pose.y:.1f})")
        print(f"  LiDAR: {len(scan.ranges)} rays, nearest obstacle: {min(scan.ranges):.2f}m")
        print()

        # Navigate through waypoints (avoiding obstacles in office_v2)
        waypoints = [
            Pose2D(x=2.0, y=3.0, theta=0.0),
            Pose2D(x=7.0, y=3.5, theta=0.0),
            Pose2D(x=13.0, y=5.0, theta=0.0),
            Pose2D(x=15.0, y=7.0, theta=0.0),
            Pose2D(x=12.0, y=10.0, theta=0.0),
        ]

        print(f"  Following path: {len(waypoints)} waypoints")
        print()

        result = await robot.follow_path(waypoints)

        # Final report
        print()
        final_pose = robot.get_pose()
        print(f"  Final pose: ({final_pose.x:.1f}, {final_pose.y:.1f})")
        print(f"  Total distance: {result.distance:.1f}m")
        print(f"  Result: {'success' if result.success else 'blocked — ' + result.reason}")
        print()
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
