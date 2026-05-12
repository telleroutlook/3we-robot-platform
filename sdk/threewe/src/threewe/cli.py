# SPDX-License-Identifier: Apache-2.0
"""CLI entry point for threewe commands."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="threewe",
        description="3we Robot Platform — AI-First Python API",
    )
    subparsers = parser.add_subparsers(dest="command")

    launch_parser = subparsers.add_parser("launch", help="Launch a simulation backend")
    launch_parser.add_argument("--backend", default="gazebo", choices=["gazebo", "isaac_sim"])
    launch_parser.add_argument("--scene", default="office_v2")
    launch_parser.add_argument("--headless", action="store_true", help="Run without GUI")
    launch_parser.add_argument("--rviz", action="store_true", help="Launch RViz2 alongside")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmarks")
    benchmark_sub = benchmark_parser.add_subparsers(dest="bench_cmd")
    run_parser = benchmark_sub.add_parser("run", help="Run a benchmark task")
    run_parser.add_argument(
        "--task", required=True, choices=["pointnav", "objectnav", "exploration"]
    )
    run_parser.add_argument("--episodes", type=int, default=100)
    run_parser.add_argument("--backend", default="gazebo")
    run_parser.add_argument("--scene", default="office_v2")

    args = parser.parse_args()

    if args.command == "launch":
        _cmd_launch(args)
    elif args.command == "benchmark":
        _cmd_benchmark(args)
    else:
        parser.print_help()
        sys.exit(1)


def _find_ros2_ws() -> str | None:
    """Locate the ros2_ws directory by walking up from this package."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        candidate = os.path.join(current, "ros2_ws")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _cmd_launch(args: argparse.Namespace) -> None:
    if args.backend == "isaac_sim":
        print("Error: Isaac Sim backend is not yet available (Phase 2).", file=sys.stderr)
        sys.exit(1)

    if shutil.which("ros2") is None:
        print(
            "Error: 'ros2' command not found. Install ROS2 Jazzy:\n"
            "  https://docs.ros.org/en/jazzy/Installation.html",
            file=sys.stderr,
        )
        sys.exit(1)

    ros2_ws = _find_ros2_ws()
    if ros2_ws is None:
        print(
            "Error: Could not locate ros2_ws directory. "
            "Run from within the 3we-robot-platform repository.",
            file=sys.stderr,
        )
        sys.exit(1)

    launch_file = os.path.join(ros2_ws, "robot_simulation", "launch", "gazebo.launch.py")
    if not os.path.isfile(launch_file):
        print(f"Error: Launch file not found: {launch_file}", file=sys.stderr)
        sys.exit(1)

    cmd = ["ros2", "launch", "robot_simulation", "gazebo.launch.py"]
    cmd.append(f"world:={args.scene}")

    if args.headless:
        cmd.append("headless:=true")
    if args.rviz:
        cmd.append("rviz:=true")

    print(f"Launching Gazebo with scene '{args.scene}'...")
    print(f"  Command: {' '.join(cmd)}")
    print("  Press Ctrl+C to stop.\n")

    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        process.terminate()
        process.wait(timeout=10)
    except FileNotFoundError:
        print("Error: Failed to execute ros2 launch command.", file=sys.stderr)
        sys.exit(1)

    sys.exit(process.returncode or 0)


def _cmd_benchmark(args: argparse.Namespace) -> None:
    if not hasattr(args, "bench_cmd") or args.bench_cmd is None:
        print("Usage: threewe benchmark run --task <task>")
        sys.exit(1)

    from threewe.benchmark.runner import run_benchmark_cli

    run_benchmark_cli(
        task=args.task,
        episodes=args.episodes,
        backend=args.backend,
        scene=args.scene,
    )


if __name__ == "__main__":
    main()
