# SPDX-License-Identifier: Apache-2.0
"""Sim2Real Demo — Same code runs on simulation and real hardware.

Usage:
    # Run in simulation (default)
    python examples/sim2real_demo.py

    # Run on real hardware (requires ROS2 + robot_bringup running)
    python examples/sim2real_demo.py --backend real
"""

import argparse
import asyncio

from threewe import Robot


async def run_demo(backend: str):
    print(f"Running on backend: {backend}")
    print("=" * 40)

    async with Robot(backend=backend) as robot:
        # 1. Check sensors
        pose = robot.get_pose()
        print(f"[1] Pose: ({pose.x:.2f}, {pose.y:.2f}, {pose.theta:.2f})")

        image = robot.get_image()
        print(f"[2] Camera: {image.shape} {image.dtype}")

        scan = robot.get_lidar_scan()
        print(f"[3] LiDAR: {scan.ranges.shape[0]} points, max={scan.range_max}m")

        imu = robot.get_imu()
        print(
            f"[4] IMU accel: [{imu.acceleration[0]:.2f}, {imu.acceleration[1]:.2f}, {imu.acceleration[2]:.2f}]"
        )

        battery = robot.get_battery_state()
        print(f"[5] Battery: {battery.voltage:.1f}V ({battery.percentage * 100:.0f}%)")

        # 2. Move forward
        print("\n[6] Moving forward 0.5m...")
        result = await robot.move_forward(0.5)
        print(f"    Result: {result.reason}, distance={result.distance:.2f}m")

        # 3. Rotate
        print("[7] Rotating 90 degrees...")
        result = await robot.rotate(1.57)
        print(f"    Result: {result.reason}")

        # 4. Navigate to point
        print("[8] Navigating to (1.0, 1.0)...")
        result = await robot.move_to(x=1.0, y=1.0)
        print(
            f"    Result: {result.reason}, final=({result.final_pose.x:.2f}, {result.final_pose.y:.2f})"
        )

    print("\n" + "=" * 40)
    print("Demo complete. Same code, any backend.")


def main():
    parser = argparse.ArgumentParser(description="Sim2Real demonstration")
    parser.add_argument("--backend", default="gazebo", choices=["gazebo", "real"])
    args = parser.parse_args()
    asyncio.run(run_demo(args.backend))


if __name__ == "__main__":
    main()
