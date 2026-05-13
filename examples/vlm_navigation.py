# SPDX-License-Identifier: Apache-2.0
"""VLM-powered visual navigation — navigate using natural language commands.

This example demonstrates the full VLM perception-action loop:
1. Robot captures camera image
2. VLM (GPT-4o / Qwen-VL) analyzes the scene
3. VLM outputs a single navigation action (JSON)
4. Robot executes the action
5. Repeat until task is complete or max steps reached

Prerequisites:
    pip install threewe[ai]
    export OPENAI_API_KEY=sk-...

    For Qwen-VL via compatible endpoint:
    export THREEWE_VLM_MODEL=qwen-vl-max
    export THREEWE_VLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    export OPENAI_API_KEY=sk-your-dashscope-key

Usage:
    python examples/vlm_navigation.py
    python examples/vlm_navigation.py --backend real
    python examples/vlm_navigation.py --instruction "找到红色水瓶并靠近它"
"""

import argparse
import asyncio
import time

from threewe import Robot
from threewe.ai import VLMRunner


def print_step(step: int, raw_response: str, action: dict) -> None:
    """Callback to print each VLM reasoning step."""
    print(f"\n{'─' * 60}")
    print(f"  Step {step + 1}")
    print(f"{'─' * 60}")
    if action:
        print(f"  Action:  {action.get('action', '?')}")
        if "distance" in action:
            print(f"  Distance: {action['distance']:.2f} m")
        if "angle" in action:
            print(f"  Angle:   {action['angle']:.2f} rad")
        print(f"  Reason:  {action.get('reason', '—')}")
    else:
        print("  [VLM returned invalid JSON, retrying...]")
        print(f"  Raw: {raw_response[:100]}")


async def run_vlm_navigation(backend: str, instruction: str, max_steps: int) -> None:
    """Run VLM navigation with step-by-step output."""

    vlm = VLMRunner.from_env(max_steps=max_steps)

    print(f"\n{'═' * 60}")
    print("  3we VLM Navigation Demo")
    print(f"{'═' * 60}")
    print(f"  Backend:     {backend}")
    print(f"  Model:       {vlm._model}")
    print(f"  Instruction: {instruction}")
    print(f"  Max steps:   {max_steps}")
    print(f"{'═' * 60}\n")

    async with Robot(backend=backend) as robot:
        start_time = time.time()
        start_pose = robot.get_pose()
        print(f"  Start pose: x={start_pose.x:.2f}, y={start_pose.y:.2f}, θ={start_pose.theta:.2f}")

        from threewe.ai.vlm_runner import execute_vlm_instruction

        result = await execute_vlm_instruction(
            robot,
            instruction,
            model=vlm._model,
            api_key=vlm._api_key,
            base_url=vlm._base_url,
            max_steps=max_steps,
            on_step=print_step,
        )

        elapsed = time.time() - start_time
        end_pose = robot.get_pose()

        print(f"\n{'═' * 60}")
        print("  Result")
        print(f"{'═' * 60}")
        print(f"  Success:     {'Yes' if result.success else 'No'}")
        print(f"  Description: {result.description}")
        print(f"  Steps taken: {len(result.images)}")
        print(f"  Time:        {elapsed:.1f}s")
        print(f"  End pose:    x={end_pose.x:.2f}, y={end_pose.y:.2f}, θ={end_pose.theta:.2f}")
        distance = ((end_pose.x - start_pose.x) ** 2 + (end_pose.y - start_pose.y) ** 2) ** 0.5
        print(f"  Distance:    {distance:.2f} m")
        print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="VLM visual navigation demo")
    parser.add_argument(
        "--backend",
        default="mock",
        choices=["mock", "gazebo", "real", "isaac_sim"],
        help="Robot backend (default: mock; use gazebo/isaac_sim for simulation)",
    )
    parser.add_argument(
        "--instruction",
        default="Navigate to the red object and stop near it",
        help="Natural language navigation instruction",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=15,
        help="Maximum VLM reasoning steps (default: 15)",
    )
    args = parser.parse_args()

    asyncio.run(run_vlm_navigation(args.backend, args.instruction, args.max_steps))


if __name__ == "__main__":
    main()
