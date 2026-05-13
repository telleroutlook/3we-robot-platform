# SPDX-License-Identifier: Apache-2.0
"""Sim2Real Validation Report Demo — demonstrates the transfer validation pipeline.

Runs the standard Sim2Real test suite using the MockBackend (no ROS2 required)
and prints a formatted Markdown report showing transfer ratios and pass/fail status.

Usage:
    python examples/sim2real_report_demo.py
"""

import asyncio


async def main():
    from threewe.benchmark.sim2real import generate_demo_report

    print("Running Sim2Real transfer validation (demo mode)...\n")
    report = await generate_demo_report(num_trials=3)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
