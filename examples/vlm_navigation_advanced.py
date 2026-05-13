# SPDX-License-Identifier: Apache-2.0
"""Advanced VLM navigation — multi-model comparison with evaluation metrics.

Runs the same instruction across multiple VLM backends and compares:
- Success rate
- Steps to completion
- Total time
- Distance traveled

Outputs a JSON report for quantitative analysis.

Prerequisites:
    pip install threewe[ai]
    export OPENAI_API_KEY=sk-...

    For Qwen-VL comparison (optional):
    export QWEN_API_KEY=sk-...
    export QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

Usage:
    python examples/vlm_navigation_advanced.py
    python examples/vlm_navigation_advanced.py --episodes 5 --output results.json
"""

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from threewe import Robot
from threewe.ai.vlm_runner import execute_vlm_instruction


@dataclass
class EpisodeResult:
    model: str
    instruction: str
    success: bool
    steps: int
    elapsed_seconds: float
    distance_traveled: float
    reason: str


@dataclass
class BenchmarkReport:
    timestamp: str
    backend: str
    episodes_per_model: int
    instructions: list[str]
    results: list[EpisodeResult] = field(default_factory=list)

    def summary(self) -> dict:
        by_model: dict[str, list[EpisodeResult]] = {}
        for r in self.results:
            by_model.setdefault(r.model, []).append(r)

        summary = {}
        for model, episodes in by_model.items():
            successes = [e for e in episodes if e.success]
            summary[model] = {
                "success_rate": len(successes) / len(episodes) if episodes else 0,
                "avg_steps": sum(e.steps for e in episodes) / len(episodes) if episodes else 0,
                "avg_time_s": (
                    sum(e.elapsed_seconds for e in episodes) / len(episodes) if episodes else 0
                ),
                "avg_distance_m": (
                    sum(e.distance_traveled for e in episodes) / len(episodes) if episodes else 0
                ),
                "total_episodes": len(episodes),
            }
        return summary


DEFAULT_INSTRUCTIONS = [
    "Navigate to the red object and stop near it",
    "找到红色水瓶并靠近它",
    "Go to the nearest doorway",
    "Explore until you find a chair, then stop",
]


async def run_episode(
    backend: str,
    model: str,
    instruction: str,
    api_key: str | None,
    base_url: str | None,
    max_steps: int,
) -> EpisodeResult:
    """Run a single VLM navigation episode and return metrics."""
    start_time = time.time()

    async with Robot(backend=backend) as robot:
        start_pose = robot.get_pose()

        result = await execute_vlm_instruction(
            robot,
            instruction,
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_steps=max_steps,
        )

        end_pose = robot.get_pose()
        elapsed = time.time() - start_time
        distance = ((end_pose.x - start_pose.x) ** 2 + (end_pose.y - start_pose.y) ** 2) ** 0.5

    return EpisodeResult(
        model=model,
        instruction=instruction,
        success=result.success,
        steps=len(result.images),
        elapsed_seconds=elapsed,
        distance_traveled=distance,
        reason=result.description,
    )


async def run_benchmark(
    backend: str,
    models: list[dict],
    instructions: list[str],
    episodes: int,
    max_steps: int,
    output_path: Path | None,
) -> None:
    """Run full benchmark across models and instructions."""
    import os

    report = BenchmarkReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        backend=backend,
        episodes_per_model=episodes,
        instructions=instructions,
    )

    total_runs = len(models) * len(instructions) * episodes
    run_count = 0

    for model_cfg in models:
        model_name = model_cfg["model"]
        api_key = model_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY")
        base_url = model_cfg.get("base_url")

        print(f"\n{'═' * 50}")
        print(f"  Model: {model_name}")
        print(f"{'═' * 50}")

        for instruction in instructions:
            for ep in range(episodes):
                run_count += 1
                print(f"  [{run_count}/{total_runs}] '{instruction[:40]}...' (ep {ep + 1})")

                try:
                    result = await run_episode(
                        backend=backend,
                        model=model_name,
                        instruction=instruction,
                        api_key=api_key,
                        base_url=base_url,
                        max_steps=max_steps,
                    )
                    report.results.append(result)
                    status = "OK" if result.success else "FAIL"
                    print(f"    {status} — {result.steps} steps, {result.elapsed_seconds:.1f}s")
                except Exception as e:
                    print(f"    ERROR — {e}")
                    report.results.append(
                        EpisodeResult(
                            model=model_name,
                            instruction=instruction,
                            success=False,
                            steps=0,
                            elapsed_seconds=0,
                            distance_traveled=0,
                            reason=f"error: {e}",
                        )
                    )

    # Print summary
    summary = report.summary()
    print(f"\n{'═' * 50}")
    print("  Summary")
    print(f"{'═' * 50}")
    for model, stats in summary.items():
        print(f"\n  {model}:")
        print(f"    Success rate:  {stats['success_rate']:.0%}")
        print(f"    Avg steps:     {stats['avg_steps']:.1f}")
        print(f"    Avg time:      {stats['avg_time_s']:.1f}s")
        print(f"    Avg distance:  {stats['avg_distance_m']:.2f}m")

    # Save report
    if output_path:
        output_data = {
            "timestamp": report.timestamp,
            "backend": report.backend,
            "episodes_per_model": report.episodes_per_model,
            "instructions": report.instructions,
            "summary": summary,
            "results": [asdict(r) for r in report.results],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        print(f"\n  Report saved to: {output_path}")


def main():
    import os

    parser = argparse.ArgumentParser(description="VLM multi-model navigation benchmark")
    parser.add_argument("--backend", default="gazebo", choices=["gazebo", "real", "isaac_sim"])
    parser.add_argument(
        "--episodes", type=int, default=3, help="Episodes per model per instruction"
    )
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--output", type=str, default="reports/vlm_benchmark.json")
    parser.add_argument(
        "--instructions",
        nargs="+",
        default=None,
        help="Custom instructions (default: built-in set)",
    )
    args = parser.parse_args()

    instructions = args.instructions or DEFAULT_INSTRUCTIONS

    # Configure models based on available API keys
    models = [{"model": "gpt-4o"}]

    qwen_key = os.environ.get("QWEN_API_KEY")
    qwen_url = os.environ.get("QWEN_BASE_URL")
    if qwen_key:
        models.append({"model": "qwen-vl-max", "api_key": qwen_key, "base_url": qwen_url})

    asyncio.run(
        run_benchmark(
            backend=args.backend,
            models=models,
            instructions=instructions,
            episodes=args.episodes,
            max_steps=args.max_steps,
            output_path=Path(args.output),
        )
    )


if __name__ == "__main__":
    main()
