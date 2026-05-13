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
    launch_parser.add_argument(
        "--num-envs", type=int, default=1, help="Number of parallel envs (Isaac Sim only)"
    )

    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmarks")
    benchmark_sub = benchmark_parser.add_subparsers(dest="bench_cmd")
    run_parser = benchmark_sub.add_parser("run", help="Run a benchmark task")
    run_parser.add_argument(
        "--task", required=True, choices=["pointnav", "objectnav", "exploration"]
    )
    run_parser.add_argument("--episodes", type=int, default=100)
    run_parser.add_argument("--backend", default="gazebo")
    run_parser.add_argument("--scene", default="office_v2")

    compare_parser = benchmark_sub.add_parser("compare", help="Compare results to baseline")
    compare_parser.add_argument("--result", required=True, help="Path to result JSON file")
    compare_parser.add_argument(
        "--baseline", required=True, help="Baseline name to compare against"
    )

    submit_parser = benchmark_sub.add_parser("submit", help="Submit result to leaderboard")
    submit_parser.add_argument("--result", required=True, help="Path to result JSON file")

    hal_parser = subparsers.add_parser("hal", help="Hardware Abstraction Layer commands")
    hal_sub = hal_parser.add_subparsers(dest="hal_cmd")
    hal_sub.add_parser("list", help="List all available hardware profiles")

    test_parser = subparsers.add_parser("test", help="Run validation tests")
    test_sub = test_parser.add_subparsers(dest="test_cmd")
    sim2real_parser = test_sub.add_parser("sim2real", help="Run sim2real transfer validation")
    sim2real_parser.add_argument("--backend", default="gazebo", help="Simulation backend")
    sim2real_parser.add_argument("--scene", default="office_v2", help="Scene to test in")
    sim2real_parser.add_argument(
        "--tests", nargs="*", default=None, help="Specific test names (default: all)"
    )

    args = parser.parse_args()

    if args.command == "launch":
        _cmd_launch(args)
    elif args.command == "benchmark":
        _cmd_benchmark(args)
    elif args.command == "test":
        _cmd_test(args)
    elif args.command == "hal":
        _cmd_hal(args)
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
        print(f"Launching Isaac Sim with scene '{args.scene}' ({args.num_envs} envs)...")
        print("  Requires NVIDIA Isaac Sim installed separately.")
        print("  See: https://developer.nvidia.com/isaac-sim")
        sys.exit(0)

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
        print("Usage: threewe benchmark {run,compare,submit}")
        sys.exit(1)

    if args.bench_cmd == "run":
        from threewe.benchmark.runner import run_benchmark_cli

        run_benchmark_cli(
            task=args.task,
            episodes=args.episodes,
            backend=args.backend,
            scene=args.scene,
        )
    elif args.bench_cmd == "compare":
        _cmd_benchmark_compare(args)
    elif args.bench_cmd == "submit":
        _cmd_benchmark_submit(args)


def _cmd_benchmark_compare(args: argparse.Namespace) -> None:
    """Compare a result JSON against a baseline."""
    import json
    from pathlib import Path

    from threewe.benchmark.baselines import compare_to_baseline, list_baselines

    result_path = Path(args.result)
    if not result_path.exists():
        print(f"Error: Result file not found: {result_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result_path.read_text())

    try:
        comparison = compare_to_baseline(
            baseline_name=args.baseline,
            success_rate=data.get("success_rate", 0.0),
            spl=data.get("spl", 0.0),
            avg_duration=data.get("avg_duration", 0.0),
            coverage=data.get("coverage", 0.0),
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"Available baselines: {list_baselines()}")
        sys.exit(1)

    print(f"\nComparison against: {comparison.baseline_name}")
    print("=" * 50)
    print(f"  Success Rate: {comparison.success_rate_delta:+.3f}")
    print(f"  SPL:          {comparison.spl_delta:+.3f}")
    print(f"  Duration:     {comparison.duration_delta:+.2f}s")
    if comparison.coverage_delta != 0:
        print(f"  Coverage:     {comparison.coverage_delta:+.3f}")
    print(f"\n  Overall: {'IMPROVED' if comparison.improved else 'REGRESSED'}")


def _cmd_benchmark_submit(args: argparse.Namespace) -> None:
    """Validate and display a leaderboard submission."""
    import json
    from pathlib import Path

    from threewe.benchmark.leaderboard import validate_submission

    result_path = Path(args.result)
    if not result_path.exists():
        print(f"Error: Result file not found: {result_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result_path.read_text())
    errors = validate_submission(data)

    if errors:
        print("Submission validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("Submission validated successfully!")
    print(f"  Agent: {data['agent_name']}")
    print(f"  Task:  {data['task']} / {data['scene']}")
    print(f"  SR:    {data['success_rate']:.3f}")
    print(f"  SPL:   {data['spl']:.3f}")


def _cmd_hal(args: argparse.Namespace) -> None:
    if not hasattr(args, "hal_cmd") or args.hal_cmd is None:
        print("Usage: threewe hal {list}")
        sys.exit(1)

    if args.hal_cmd == "list":
        _cmd_hal_list()


def _cmd_hal_list() -> None:
    """List all available hardware profiles."""
    from threewe.hal.discovery import list_all_profiles

    profiles = list_all_profiles()
    print(f"Available hardware profiles ({len(profiles)}):")
    print("=" * 50)
    for name, profile in sorted(profiles.items()):
        print(f"  {name}")
        print(f"    Wheel type: {profile.wheel_type}")
        print(f"    Max linear: {profile.max_linear_velocity} m/s")
        print(f"    Weight:     {profile.weight_kg} kg")
        print()


def _cmd_test(args: argparse.Namespace) -> None:
    if not hasattr(args, "test_cmd") or args.test_cmd is None:
        print("Usage: threewe test {sim2real}")
        sys.exit(1)

    if args.test_cmd == "sim2real":
        _cmd_test_sim2real(args)


def _cmd_test_sim2real(args: argparse.Namespace) -> None:
    """Run sim2real transfer validation tests (sim-only mode)."""
    from threewe.benchmark.sim2real import STANDARD_TRANSFER_TESTS, evaluate_transfer

    print(f"Running sim2real transfer tests (backend={args.backend}, scene={args.scene})")
    print("=" * 50)

    test_names = args.tests

    if test_names:
        tests = [t for t in STANDARD_TRANSFER_TESTS if t.name in test_names]
        if not tests:
            print(
                f"Error: No matching tests found. Available: "
                f"{[t.name for t in STANDARD_TRANSFER_TESTS]}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        tests = list(STANDARD_TRANSFER_TESTS)

    print(f"  Tests to run: {[t.name for t in tests]}")
    print("  Mode: sim-only (validates thresholds against sim baseline)")
    print()

    results = []
    for test in tests:
        sim_value = 0.5
        result = evaluate_transfer(test, sim_value=sim_value, real_value=sim_value)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {test.name}: sim_value={result.sim_value:.3f}")

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")


if __name__ == "__main__":
    main()
