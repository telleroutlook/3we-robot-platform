# SPDX-License-Identifier: Apache-2.0
"""ObjectNav benchmark runner — object-goal navigation episodes."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from threewe.benchmark.runner import EpisodeResult
from threewe.types import Pose2D


@dataclass(frozen=True)
class ObjectNavEpisodeConfig:
    """Configuration for a single ObjectNav episode."""

    target_category: str
    target_position: Pose2D
    start_pose: Pose2D
    success_radius: float = 1.0
    timeout: float = 60.0


async def run_objectnav_episode(robot, config: ObjectNavEpisodeConfig) -> EpisodeResult:
    """Run a single ObjectNav episode.

    The robot navigates toward the target object position. Success is
    determined by reaching within `config.success_radius` of the target.
    """
    start_time = time.time()

    start_pose = robot.get_pose()
    optimal_length = math.sqrt(
        (config.target_position.x - start_pose.x) ** 2
        + (config.target_position.y - start_pose.y) ** 2
    )

    result = await robot.move_to(
        x=config.target_position.x,
        y=config.target_position.y,
        timeout=config.timeout,
    )
    duration = time.time() - start_time

    final_pose = robot.get_pose()
    dist_to_target = math.sqrt(
        (config.target_position.x - final_pose.x) ** 2
        + (config.target_position.y - final_pose.y) ** 2
    )
    success = dist_to_target <= config.success_radius

    reason = "reached_object" if success else result.reason

    return EpisodeResult(
        episode_id=0,
        success=success,
        duration=duration,
        path_length=result.distance,
        optimal_length=optimal_length,
        reason=reason,
    )


def generate_objectnav_episodes(
    scene_name: str,
    num_episodes: int,
    seed: int = 42,
) -> list[ObjectNavEpisodeConfig]:
    """Generate ObjectNav episode configs from a scene's goal poses.

    Each episode picks a random object category and goal pose from the scene.
    """
    import numpy as np

    from threewe.benchmark.tasks import ObjectNavTask
    from threewe.scenes import load_scene

    rng = np.random.default_rng(seed)
    scene = load_scene(scene_name)
    task = ObjectNavTask()

    episodes: list[ObjectNavEpisodeConfig] = []
    for _ in range(num_episodes):
        goal = scene.goal_poses[rng.integers(0, len(scene.goal_poses))]
        category = task.object_categories[rng.integers(0, len(task.object_categories))]
        start = scene.start_poses[rng.integers(0, len(scene.start_poses))]

        episodes.append(
            ObjectNavEpisodeConfig(
                target_category=category,
                target_position=goal,
                start_pose=start,
                success_radius=1.0,
                timeout=60.0,
            )
        )

    return episodes


async def run_objectnav_benchmark(
    backend: str = "gazebo",
    scene: str = "office_v2",
    num_episodes: int = 100,
    seed: int = 42,
) -> list[EpisodeResult]:
    """Run a full ObjectNav benchmark and return episode results."""
    from threewe import Robot

    configs = generate_objectnav_episodes(scene, num_episodes, seed)
    episodes: list[EpisodeResult] = []

    async with Robot(backend=backend, scene=scene, auto_connect=True) as robot:
        for i, config in enumerate(configs):
            result = await run_objectnav_episode(robot, config)
            episodes.append(
                EpisodeResult(
                    episode_id=i,
                    success=result.success,
                    duration=result.duration,
                    path_length=result.path_length,
                    optimal_length=result.optimal_length,
                    reason=result.reason,
                )
            )

    return episodes
