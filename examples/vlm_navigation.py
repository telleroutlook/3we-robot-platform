# SPDX-License-Identifier: Apache-2.0
"""VLM-powered visual navigation — navigate using natural language commands.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/vlm_navigation.py
"""

import asyncio

from threewe import Robot


async def main():
    async with Robot(backend="gazebo") as robot:
        # Execute a natural language navigation instruction
        result = await robot.execute_instruction(
            "Navigate to the red door at the end of the hallway"
        )

        print(f"Execution: {'success' if result.success else 'failed'}")
        print(f"Description: {result.description}")
        print(f"Images captured: {len(result.images)}")


if __name__ == "__main__":
    asyncio.run(main())
