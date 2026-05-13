# SPDX-License-Identifier: Apache-2.0
"""VLM navigation video demo — record navigation with decision overlay.

Records the VLM navigation process as an MP4 video with:
- Robot camera feed as the background
- HUD overlay showing VLM decisions (action, reason, step count)
- Final summary frame with metrics

Output is suitable for social media sharing (Twitter/Zhihu/YouTube).

Prerequisites:
    pip install threewe[ai] opencv-python
    export OPENAI_API_KEY=sk-...

Usage:
    python examples/vlm_video_demo.py
    python examples/vlm_video_demo.py --output demo_navigation.mp4
    python examples/vlm_video_demo.py --instruction "找到红色水瓶并靠近它"
"""

import argparse
import asyncio
import time
from pathlib import Path

import numpy as np

from threewe import Robot
from threewe.ai import VLMRunner


class VideoRecorder:
    """Records frames with HUD overlay to MP4."""

    def __init__(self, output_path: str, fps: int = 5, resolution: tuple[int, int] = (640, 480)):
        try:
            import cv2
        except ImportError as e:
            raise ImportError(
                "opencv-python is required for video recording. "
                "Install with: pip install opencv-python"
            ) from e

        self._cv2 = cv2
        self._fps = fps
        self._resolution = resolution
        self._output_path = output_path
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(output_path, fourcc, fps, resolution)
        self._frame_count = 0

    def add_frame(
        self,
        image: np.ndarray,
        step: int,
        action: str = "",
        reason: str = "",
        instruction: str = "",
    ) -> None:
        """Add a frame with HUD overlay."""
        cv2 = self._cv2
        frame = cv2.resize(image, self._resolution)

        if frame.shape[2] == 3 and frame.dtype == np.uint8:
            frame = frame.copy()

        overlay = frame.copy()
        h, w = frame.shape[:2]
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        cv2.rectangle(overlay, (0, h - 50), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX

        cv2.putText(frame, f"Step {step + 1}", (10, 25), font, 0.6, (0, 255, 255), 1)
        cv2.putText(frame, f"Action: {action}", (10, 50), font, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Reason: {reason[:60]}", (10, 70), font, 0.4, (200, 200, 200), 1)

        instr_display = instruction[:50] + ("..." if len(instruction) > 50 else "")
        cv2.putText(frame, instr_display, (10, h - 15), font, 0.4, (100, 255, 100), 1)

        self._writer.write(frame)
        self._frame_count += 1

    def add_summary_frame(
        self,
        success: bool,
        total_steps: int,
        elapsed: float,
        distance: float,
        instruction: str,
        duration_frames: int = 15,
    ) -> None:
        """Add a summary frame held for several seconds."""
        cv2 = self._cv2
        w, h = self._resolution

        for _ in range(duration_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (30, 30, 30)

            font = cv2.FONT_HERSHEY_SIMPLEX
            color_success = (0, 255, 0) if success else (0, 0, 255)
            status_text = "SUCCESS" if success else "FAILED"

            cv2.putText(
                frame, "3we VLM Navigation", (w // 2 - 140, 60), font, 0.8, (255, 255, 255), 2
            )
            cv2.putText(frame, status_text, (w // 2 - 60, 120), font, 1.0, color_success, 2)

            y = 180
            metrics = [
                f"Instruction: {instruction[:45]}",
                f"Steps: {total_steps}",
                f"Time: {elapsed:.1f}s",
                f"Distance: {distance:.2f}m",
            ]
            for line in metrics:
                cv2.putText(frame, line, (40, y), font, 0.5, (200, 200, 200), 1)
                y += 30

            cv2.putText(
                frame,
                "github.com/3we-org/3we-robot-platform",
                (w // 2 - 180, h - 30),
                font,
                0.4,
                (100, 100, 100),
                1,
            )

            self._writer.write(frame)

    def close(self) -> None:
        self._writer.release()
        print(f"  Video saved: {self._output_path} ({self._frame_count} frames)")


async def run_video_demo(backend: str, instruction: str, max_steps: int, output: str) -> None:
    """Run VLM navigation and record to video."""

    vlm = VLMRunner.from_env(max_steps=max_steps)
    recorder = VideoRecorder(output, fps=5)

    print(f"\n{'═' * 50}")
    print("  3we VLM Video Demo")
    print(f"{'═' * 50}")
    print(f"  Backend:     {backend}")
    print(f"  Model:       {vlm._model}")
    print(f"  Instruction: {instruction}")
    print(f"  Output:      {output}")
    print(f"{'═' * 50}\n")

    async with Robot(backend=backend) as robot:
        import json

        start_time = time.time()
        start_pose = robot.get_pose()
        step_count = 0
        success = False
        description = ""

        for step in range(max_steps):
            image = robot.get_image()

            try:
                response_text = vlm.plan(image, instruction)
                action = json.loads(response_text)
            except (json.JSONDecodeError, Exception):
                recorder.add_frame(image, step, action="[parsing...]", instruction=instruction)
                continue

            cmd = action.get("action", "stop")
            reason = action.get("reason", "")
            step_count = step + 1

            recorder.add_frame(image, step, action=cmd, reason=reason, instruction=instruction)
            print(f"  Step {step + 1}: {cmd} — {reason[:50]}")

            if cmd == "done":
                success = True
                description = reason
                break
            elif cmd == "move_forward":
                await robot.move_forward(float(action.get("distance", 0.3)))
            elif cmd == "rotate_left":
                await robot.rotate(float(action.get("angle", 0.5)))
            elif cmd == "rotate_right":
                await robot.rotate(-float(action.get("angle", 0.5)))
            elif cmd == "stop":
                robot.stop()

        elapsed = time.time() - start_time
        end_pose = robot.get_pose()
        distance = ((end_pose.x - start_pose.x) ** 2 + (end_pose.y - start_pose.y) ** 2) ** 0.5

        recorder.add_summary_frame(
            success=success,
            total_steps=step_count,
            elapsed=elapsed,
            distance=distance,
            instruction=instruction,
        )
        recorder.close()

        print(f"\n  {'Success' if success else 'Failed'}: {description or 'max steps reached'}")
        print(f"  {step_count} steps, {elapsed:.1f}s, {distance:.2f}m traveled")


def main():
    parser = argparse.ArgumentParser(description="VLM navigation video recorder")
    parser.add_argument("--backend", default="gazebo", choices=["gazebo", "real", "isaac_sim"])
    parser.add_argument("--instruction", default="Navigate to the red object and stop near it")
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--output", default="vlm_demo.mp4", help="Output video path")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(run_video_demo(args.backend, args.instruction, args.max_steps, args.output))


if __name__ == "__main__":
    main()
