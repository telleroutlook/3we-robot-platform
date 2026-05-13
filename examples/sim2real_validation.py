# SPDX-License-Identifier: Apache-2.0
"""Sim2Real validation example — run transfer tests and generate a report.

Demonstrates the Sim2Real validation framework:
1. Define transfer tests with pass/fail criteria
2. Run tests in simulation (and optionally on real hardware)
3. Compare metrics to determine transfer quality
4. Generate a structured report

Usage:
    python examples/sim2real_validation.py
    python examples/sim2real_validation.py --backend gazebo --trials 10
"""

import argparse
import asyncio
import time

from threewe.benchmark.sim2real import (
    STANDARD_TRANSFER_TESTS,
    Sim2RealValidator,
    evaluate_transfer,
)


def demo_evaluation_only() -> None:
    """Demonstrate the evaluation logic without running a real robot.

    This uses hypothetical sim/real values to show how the
    transfer quality assessment works.
    """
    print("=" * 60)
    print("  Sim2Real Transfer Evaluation Demo")
    print("  (Using example sim/real values — no robot required)")
    print("=" * 60)

    example_data = [
        ("straight_walk_5m", 0.05, 0.08),
        ("rotation_360", 2.1, 4.5),
        ("obstacle_avoidance_3", 0.95, 0.72),
        ("pointnav_10m", 0.85, 0.55),
        ("dynamic_obstacle", 0.10, 0.18),
    ]

    print(f"\n{'Test':<25} {'Sim':>8} {'Real':>8} {'Ratio':>8} {'Status':>8}")
    print("-" * 60)

    results = []
    for test in STANDARD_TRANSFER_TESTS:
        for name, sim_val, real_val in example_data:
            if test.name == name:
                result = evaluate_transfer(test, sim_value=sim_val, real_value=real_val)
                results.append(result)
                status = "PASS" if result.passed else "FAIL"
                print(
                    f"  {test.name:<23} {sim_val:>8.3f} {real_val:>8.3f} "
                    f"{result.transfer_ratio:>8.2f} {status:>8}"
                )
                break

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n  Overall: {passed}/{total} passed ({passed / total:.0%})")
    print("  Threshold for PASS: >= 80%")
    print(f"  Status: {'PASS' if passed / total >= 0.8 else 'FAIL'}")


async def demo_sim_validation(backend: str, trials: int) -> None:
    """Run actual sim-only validation using the Sim2RealValidator.

    This requires a running simulation backend.
    """
    print("\n" + "=" * 60)
    print(f"  Running Sim-Only Validation (backend={backend}, trials={trials})")
    print("=" * 60)

    validator = Sim2RealValidator()

    print(f"\n  Tests: {[t.name for t in validator.tests]}")
    print(f"  Running {trials} trials per test in simulation...\n")

    for test in validator.tests:
        start = time.time()
        try:
            value = await validator.run_test_sim_only(test, backend=backend, num_trials=trials)
            elapsed = time.time() - start
            print(f"  {test.name:<25} value={value:.4f}  ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  {test.name:<25} ERROR: {e}")

    print("\n  Done. Use 'threewe sim2real report' for full Markdown output.")


def main():
    parser = argparse.ArgumentParser(description="Sim2Real validation example")
    parser.add_argument("--backend", default="gazebo", choices=["gazebo", "isaac_sim"])
    parser.add_argument("--trials", type=int, default=3, help="Trials per test")
    parser.add_argument(
        "--sim-run",
        action="store_true",
        help="Actually run tests in simulation (requires running backend)",
    )
    args = parser.parse_args()

    demo_evaluation_only()

    if args.sim_run:
        asyncio.run(demo_sim_validation(args.backend, args.trials))
    else:
        print("\n  Tip: Add --sim-run to execute tests against a live simulation backend.")
        print("  Tip: Use 'threewe sim2real report --output reports/' for automated reports.")


if __name__ == "__main__":
    main()
