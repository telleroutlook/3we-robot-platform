# SPDX-License-Identifier: Apache-2.0
"""VLM-driven instruction execution.

Supports pluggable VLM backends:
- OpenAI GPT-4o / GPT-4-turbo (via openai SDK)
- Qwen-VL (via OpenAI-compatible API)
- Local models (via custom endpoint)
"""

from __future__ import annotations

import base64
import io
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from threewe.types import ExecutionResult

if TYPE_CHECKING:
    from threewe.robot import Robot

StepCallback = Callable[[int, str, dict], None]


class VLMRunner:
    """Runs VLM inference for robot instruction execution."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        max_steps: int = 20,
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._max_steps = max_steps
        self._temperature = temperature
        self._client = None

    @classmethod
    def from_env(cls, max_steps: int = 20, temperature: float = 0.0) -> VLMRunner:
        """Create a VLMRunner from environment variables.

        Reads:
            THREEWE_VLM_MODEL: Model name (default: gpt-4o)
            OPENAI_API_KEY: API key for OpenAI or compatible endpoint
            THREEWE_VLM_BASE_URL: Custom API endpoint (for Qwen-VL, local models)
            THREEWE_VLM_MAX_STEPS: Max steps per instruction (default: 20)
            THREEWE_VLM_TEMPERATURE: Sampling temperature (default: 0.0)
        """
        return cls(
            model=os.environ.get("THREEWE_VLM_MODEL", "gpt-4o"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("THREEWE_VLM_BASE_URL"),
            max_steps=int(os.environ.get("THREEWE_VLM_MAX_STEPS", str(max_steps))),
            temperature=float(os.environ.get("THREEWE_VLM_TEMPERATURE", str(temperature))),
        )

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai package is required for VLM integration. "
                "Install with: pip install threewe[ai]"
            ) from e

        kwargs = {}
        if self._api_key is not None:
            kwargs["api_key"] = self._api_key
        if self._base_url is not None:
            kwargs["base_url"] = self._base_url

        self._client = OpenAI(**kwargs)
        return self._client

    def _encode_image(self, image: np.ndarray) -> str:
        try:
            from PIL import Image
        except ImportError as e:
            raise ImportError(
                "Pillow is required for image encoding. Install with: pip install threewe[ai]"
            ) from e

        if image.ndim == 2:
            pil_image = Image.fromarray(image, mode="L")
        elif image.ndim == 3 and image.shape[2] == 3:
            pil_image = Image.fromarray(image[:, :, ::-1])
        elif image.ndim == 3 and image.shape[2] == 4:
            pil_image = Image.fromarray(image[:, :, 2::-1])  # BGRA -> RGB
        else:
            pil_image = Image.fromarray(image)

        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _build_system_prompt(self, instruction: str) -> str:
        base_prompt = (
            "You are a robot navigation assistant. "
            "Given an image from the robot's camera "
            "and an instruction, output a single JSON action: "
            '{"action": "move_forward"|"rotate_left"|'
            '"rotate_right"|"stop"|"done", '
            '"distance": <meters>, "angle": <radians>, '
            '"reason": "<brief>"}. '
            "Only output valid JSON, nothing else."
        )
        has_cjk = any("一" <= ch <= "鿿" for ch in instruction)
        if has_cjk:
            base_prompt += (
                " The instruction is in Chinese. "
                "Respond with reason in Chinese but keep action keys in English."
            )
        return base_prompt

    def plan(self, image: np.ndarray, instruction: str) -> str:
        """Get a single-step action plan from the VLM given an image and instruction."""
        client = self._get_client()
        b64_image = self._encode_image(image)

        response = client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {
                    "role": "system",
                    "content": self._build_system_prompt(instruction),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                },
            ],
            max_tokens=200,
        )

        return response.choices[0].message.content or '{"action": "stop", "reason": "no response"}'


async def execute_vlm_instruction(
    robot: Robot,
    instruction: str,
    model: str = "gpt-4o",
    api_key: str | None = None,
    base_url: str | None = None,
    max_steps: int = 20,
    on_step: StepCallback | None = None,
) -> ExecutionResult:
    """Execute a natural language instruction using a VLM in a perception-action loop.

    The VLM observes camera images and generates navigation actions
    until the instruction is fulfilled or max_steps is reached.

    Args:
        robot: Connected Robot instance.
        instruction: Natural language task description.
        model: VLM model name.
        api_key: Optional API key override.
        base_url: Optional API base URL override.
        max_steps: Maximum perception-action cycles.
        on_step: Optional callback invoked after each step with
            (step_number, raw_response, parsed_action).
    """
    import json

    runner = VLMRunner(model=model, api_key=api_key, base_url=base_url, max_steps=max_steps)
    images_collected: list = []

    for step in range(max_steps):
        image = robot.get_image()
        images_collected.append(image)

        try:
            response_text = runner.plan(image, instruction)
            action = json.loads(response_text)
        except json.JSONDecodeError:
            if on_step:
                on_step(step, response_text if "response_text" in dir() else "", {})
            continue
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("VLM step %d error: %s", step, e)
            if on_step:
                on_step(step, "", {})
            continue

        if on_step:
            on_step(step, response_text, action)

        cmd = action.get("action", "stop")

        if cmd == "done":
            return ExecutionResult(
                success=True,
                description=action.get("reason", "instruction completed"),
                images=images_collected,
            )
        elif cmd == "move_forward":
            dist = float(action.get("distance", 0.3))
            await robot.move_forward(dist)
        elif cmd == "rotate_left":
            angle = float(action.get("angle", 0.5))
            await robot.rotate(angle)
        elif cmd == "rotate_right":
            angle = float(action.get("angle", 0.5))
            await robot.rotate(-angle)
        elif cmd == "stop":
            robot.stop()

    return ExecutionResult(
        success=False,
        description=f"max steps ({max_steps}) reached without completion",
        images=images_collected,
    )
