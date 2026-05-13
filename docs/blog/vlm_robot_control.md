# 30 Lines of Python: Let GPT-4o Control a Real Robot

What if you could give a robot a natural language instruction and have it understand, plan, and act autonomously -- all in 30 lines of Python? No ROS2 knowledge. No custom planners. No prompt engineering gymnastics.

With the `threewe` package, this is not a hypothetical. It works today, in Gazebo simulation and on real hardware, with the same code.

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        result = await robot.execute_instruction("find the red bottle and stop near it")
        print(f"Success: {result.success}")
        print(f"Description: {result.description}")

asyncio.run(main())
```

That is the entire program. The robot sees through its camera, reasons about what it sees using GPT-4o, and executes motion commands until the task is complete. Let us break down what happens inside.

---

## The VLM Perception-Action Loop

When you call `robot.execute_instruction(...)`, the SDK launches a tight perception-action loop internally. Each iteration:

1. **Capture** -- The robot takes an image from its camera (`robot.get_image()`)
2. **Reason** -- The image + instruction are sent to GPT-4o (or any OpenAI-compatible VLM)
3. **Parse** -- The model returns a structured JSON action
4. **Execute** -- The robot executes the action (move forward, rotate, stop)
5. **Repeat** -- Until the model outputs `"done"` or the step limit is reached

This loop runs up to 20 steps by default, configurable per call.

### The Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Perception-Action Loop                     │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐ │
│  │  Camera   │───▶│  VLM API │───▶│  Parser  │───▶│ Motor │ │
│  │  Image    │    │  GPT-4o  │    │  JSON    │    │  Cmd  │ │
│  └──────────┘    └──────────┘    └──────────┘    └───────┘ │
│       ▲                                               │      │
│       └───────────────────────────────────────────────┘      │
│                         Loop until "done"                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Understanding the VLMRunner

Under the hood, `execute_instruction` delegates to the `VLMRunner` class. You can use it directly for more control:

```python
import asyncio
from threewe import Robot
from threewe.ai.vlm_runner import VLMRunner

async def main():
    runner = VLMRunner(
        model="gpt-4o",
        max_steps=30,
        temperature=0.0,
    )

    async with Robot(backend="gazebo", scene="office_v2") as robot:
        # Single-step reasoning: get one action plan from current view
        image = robot.get_image()
        action_json = runner.plan(image, "go to the door on the left")
        print(f"VLM decided: {action_json}")

asyncio.run(main())
```

The `VLMRunner.plan()` method performs a single perception-reasoning step. It encodes the camera image as base64 JPEG, constructs a system prompt that constrains the model to output structured JSON, and returns the raw response.

### The Action Schema

The VLM is instructed to output exactly one JSON object per step:

```json
{
    "action": "move_forward",
    "distance": 0.5,
    "reason": "I can see a red bottle ahead on the right side"
}
```

Supported actions:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `move_forward` | `distance` (meters) | Drive straight ahead |
| `rotate_left` | `angle` (radians) | Turn counter-clockwise |
| `rotate_right` | `angle` (radians) | Turn clockwise |
| `stop` | -- | Halt motion |
| `done` | -- | Task is complete |

The constraint to structured JSON output means no free-text parsing is needed. The model either returns valid JSON or the step is skipped.

---

## Configuration via Environment Variables

The VLM runner can be configured entirely through environment variables, making it easy to swap models without code changes:

```bash
# Use GPT-4o (default)
export OPENAI_API_KEY="sk-..."

# Or use Qwen-VL via a compatible endpoint
export THREEWE_VLM_MODEL="qwen-vl-max"
export THREEWE_VLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_API_KEY="sk-..."

# Tune behavior
export THREEWE_VLM_MAX_STEPS=30
export THREEWE_VLM_TEMPERATURE=0.0
```

You can also create a runner from environment variables directly:

```python
from threewe.ai.vlm_runner import VLMRunner

runner = VLMRunner.from_env()
```

---

## Step-by-Step Callback for Debugging

When developing VLM-controlled behaviors, you want to see what the model is thinking at each step. The `on_step` callback provides this:

```python
import asyncio
import json
from threewe import Robot
from threewe.ai.vlm_runner import execute_vlm_instruction

def log_step(step_num: int, raw_response: str, parsed_action: dict) -> None:
    print(f"\n--- Step {step_num} ---")
    print(f"  Raw: {raw_response}")
    print(f"  Action: {parsed_action.get('action', 'N/A')}")
    print(f"  Reason: {parsed_action.get('reason', 'N/A')}")

async def main():
    async with Robot(backend="gazebo", scene="office_v2") as robot:
        result = await execute_vlm_instruction(
            robot,
            instruction="navigate to the kitchen area",
            model="gpt-4o",
            max_steps=25,
            on_step=log_step,
        )
        print(f"\nFinal result: success={result.success}")
        print(f"Description: {result.description}")
        print(f"Images collected: {len(result.images)}")

asyncio.run(main())
```

The output looks like this during execution:

```
--- Step 0 ---
  Raw: {"action": "rotate_left", "angle": 0.8, "reason": "Looking for kitchen, turning to scan the room"}
  Action: rotate_left
  Reason: Looking for kitchen, turning to scan the room

--- Step 1 ---
  Raw: {"action": "move_forward", "distance": 1.0, "reason": "I can see a counter and sink ahead, moving toward kitchen"}
  Action: move_forward
  Reason: I can see a counter and sink ahead, moving toward kitchen

--- Step 2 ---
  Raw: {"action": "move_forward", "distance": 0.5, "reason": "Getting closer to the kitchen counter"}
  Action: move_forward
  Reason: Getting closer to the kitchen counter

--- Step 3 ---
  Raw: {"action": "done", "reason": "I am now in the kitchen area near the counter"}
  Action: done
  Reason: I am now in the kitchen area near the counter

Final result: success=True
Description: I am now in the kitchen area near the counter
Images collected: 4
```

---

## What Happens When You Run This

Here is a concrete example. Instruction: "find the red bottle and stop near it."

**Step 0**: The robot captures its first image. It sees an office with desks, chairs, and a shelf. The VLM responds: `rotate_left, angle=0.6, reason="scanning room for red bottle"`.

**Step 1**: After rotating, the camera now shows a different angle. A shelf with various objects is visible. The VLM responds: `move_forward, distance=1.2, reason="I can see something red on the shelf ahead"`.

**Step 2**: Closer now. The VLM can clearly identify a red bottle on the second shelf. It responds: `move_forward, distance=0.8, reason="approaching the red bottle on the shelf"`.

**Step 3**: The robot is now approximately 0.3m from the shelf. The VLM responds: `done, reason="I am near the red bottle on the shelf"`.

Total execution: 4 VLM calls, roughly 3 seconds of API time, 2.5 seconds of robot motion. The `ExecutionResult` object contains `success=True`, a description, and all 4 camera images collected during execution.

---

## Sim2Real: Same Code on Real Hardware

The exact same script works on real hardware. Change one parameter:

```python
# In simulation
async with Robot(backend="gazebo") as robot:
    result = await robot.execute_instruction("find the red bottle")

# On real hardware -- literally the only change
async with Robot(backend="real") as robot:
    result = await robot.execute_instruction("find the red bottle")
```

The VLM reasoning is identical because it operates on camera images regardless of their source. The motion commands (`move_forward`, `rotate`) are executed by the Backend Abstraction Layer, which maps them to ROS2/Nav2 on real hardware and Gazebo physics in simulation.

---

## Chinese Language Support

The VLM runner detects CJK characters in instructions and adjusts its system prompt accordingly:

```python
async with Robot(backend="gazebo") as robot:
    result = await robot.execute_instruction("找到红色的瓶子并停在它旁边")
    print(f"结果: {result.description}")
```

The model will reason in Chinese for the `reason` field while keeping action keys in English for reliable parsing.

---

## Combining VLM with VLA Models

For research workflows, you might want the VLM for high-level reasoning and a VLA (Vision-Language-Action) model for fine-grained motor control:

```python
import asyncio
import numpy as np
from threewe import Robot
from threewe.ai.vlm_runner import VLMRunner
from threewe.ai.vla_runner import VLARunner

async def hybrid_control():
    vlm = VLMRunner(model="gpt-4o", max_steps=10)
    vla = VLARunner.from_pretrained("lerobot/act_3we_nav")

    async with Robot(backend="gazebo") as robot:
        for step in range(50):
            image = robot.get_image()

            # High-level: ask VLM what to do
            if step % 10 == 0:
                plan = vlm.plan(image, "navigate to the charging station")
                print(f"VLM plan: {plan}")

            # Low-level: VLA generates smooth motor commands
            obs = robot.get_observation(modalities=["image", "lidar", "velocity"])
            action = vla.predict(obs, instruction="go to charging station")
            robot.execute_action(action)

asyncio.run(hybrid_control())
```

This pattern uses the VLM as a "strategic advisor" that fires every N steps, while the VLA handles frame-by-frame motor commands with smooth trajectories.

---

## Performance Considerations

| Metric | Value |
|--------|-------|
| VLM API latency (GPT-4o) | ~800ms per step |
| Image encoding time | ~5ms |
| Total loop time per step | ~1.2s (including motion) |
| Typical task completion | 3-8 steps |
| Token usage per step | ~800 input, ~50 output |

For latency-sensitive applications, consider:

- Using `max_steps=10` for bounded execution time
- Switching to a local VLM (Qwen-VL, LLaVA) via `THREEWE_VLM_BASE_URL`
- Caching the VLM response for similar scenes
- Using the VLA runner for reactive control with VLM only for replanning

---

## Error Handling

The loop is designed to be resilient:

```python
import asyncio
from threewe import Robot, NavigationError, TimeoutError

async def robust_vlm_control():
    async with Robot(backend="gazebo") as robot:
        try:
            result = await robot.execute_instruction(
                "find the exit door and stop in front of it"
            )
            if result.success:
                print(f"Task completed: {result.description}")
            else:
                print(f"Task failed after max steps: {result.description}")
                # result.images contains all camera frames for analysis
                print(f"Collected {len(result.images)} frames for post-mortem")
        except NavigationError as e:
            print(f"Navigation failed: {e}")
        except TimeoutError as e:
            print(f"Operation timed out: {e}")

asyncio.run(robust_vlm_control())
```

If the VLM returns invalid JSON, that step is skipped and the loop continues. If a navigation action fails (obstacle, timeout), the next VLM step will see the current state and can adapt.

---

## Supported VLM Backends

| Backend | Model | Config |
|---------|-------|--------|
| OpenAI | GPT-4o, GPT-4-turbo | `OPENAI_API_KEY` |
| Qwen | Qwen-VL-Max, Qwen-VL-Plus | `THREEWE_VLM_BASE_URL` + compatible key |
| Local | LLaVA, CogVLM | Custom `base_url` pointing to local server |
| Azure OpenAI | GPT-4o | Azure endpoint via `base_url` |

Any model that supports the OpenAI chat completions API with image inputs works out of the box.

---

## Full Working Example: Object Search

Here is a complete, runnable example that searches for an object, logs each step, and saves the trajectory images:

```python
"""VLM-controlled object search.

Requirements:
    pip install threewe[ai]
    export OPENAI_API_KEY="sk-..."

Usage:
    python vlm_search.py
"""

import asyncio
import json
from pathlib import Path

from threewe import Robot
from threewe.ai.vlm_runner import execute_vlm_instruction

INSTRUCTION = "find the red bottle and stop near it"
OUTPUT_DIR = Path("vlm_results")


def on_step(step: int, raw: str, action: dict) -> None:
    print(f"[Step {step:02d}] {action.get('action', '?'):14s} | {action.get('reason', '')}")


async def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    async with Robot(backend="gazebo", scene="office_v2") as robot:
        result = await execute_vlm_instruction(
            robot,
            instruction=INSTRUCTION,
            model="gpt-4o",
            max_steps=20,
            on_step=on_step,
        )

    print(f"\n{'='*50}")
    print(f"Success: {result.success}")
    print(f"Description: {result.description}")
    print(f"Steps taken: {len(result.images)}")

    # Save trajectory images for analysis
    for i, img in enumerate(result.images):
        path = OUTPUT_DIR / f"step_{i:03d}.jpg"
        try:
            from PIL import Image
            import numpy as np

            pil_img = Image.fromarray(img[:, :, ::-1])  # BGR to RGB
            pil_img.save(str(path))
        except ImportError:
            pass

    print(f"Images saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Quick Start

### 1. Install

```bash
pip install threewe[ai]
```

This installs the core SDK plus the `openai` and `Pillow` dependencies needed for VLM integration.

### 2. Set Your API Key

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### 3. Launch Simulation (optional, for testing)

```bash
threewe launch --backend gazebo --scene office_v2
```

### 4. Run the Script

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        result = await robot.execute_instruction("find the red bottle and stop near it")
        print(f"Done! Success={result.success}: {result.description}")

asyncio.run(main())
```

### 5. Switch to Real Hardware

```python
async with Robot(backend="real") as robot:
    result = await robot.execute_instruction("find the red bottle and stop near it")
```

No other code changes required.

---

## What Comes Next

This is the simplest entry point into embodied AI. From here, you can:

- Train a VLA model using trajectories collected by VLM execution
- Use the Gymnasium environments (`threewe.gym`) for RL training
- Run benchmarks (`threewe benchmark run --task objectnav`) to measure your agent
- Submit results to the community leaderboard

The key insight is that you do not need to understand ROS2, Nav2, SLAM, or motor control to get a robot doing useful things with language. The `threewe` SDK abstracts all of that behind a Python-native interface.

---

## Links

- GitHub: [https://github.com/3we-org/3we-robot-platform](https://github.com/3we-org/3we-robot-platform)
- Documentation: [https://docs.3we.org](https://docs.3we.org)
- PyPI: [https://pypi.org/project/threewe](https://pypi.org/project/threewe)
- Discord: [https://discord.gg/3we-robotics](https://discord.gg/3we-robotics)

---

Published by the 3we team
