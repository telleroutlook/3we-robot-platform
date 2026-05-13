# SPDX-License-Identifier: Apache-2.0
"""Scene definitions for the MockBackend.

Each scene provides a room boundary and a set of axis-aligned rectangular
obstacles. The MockBackend uses these for LiDAR raycasting and collision
detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Obstacle:
    """Axis-aligned rectangular obstacle."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class MockScene:
    """Definition of a simulated 2D environment."""

    width: float
    height: float
    obstacles: tuple[Obstacle, ...] = field(default_factory=tuple)


SCENES: dict[str, MockScene] = {
    "empty": MockScene(width=20.0, height=15.0, obstacles=()),
    "office_v2": MockScene(
        width=20.0,
        height=15.0,
        obstacles=(
            Obstacle(4.0, 5.0, 6.0, 6.0),
            Obstacle(10.0, 6.0, 12.0, 7.5),
            Obstacle(3.0, 10.0, 5.0, 11.5),
            Obstacle(14.0, 2.0, 15.5, 4.5),
            Obstacle(8.0, 11.0, 10.0, 13.0),
            Obstacle(16.0, 8.0, 18.0, 9.5),
        ),
    ),
    "apartment_v1": MockScene(
        width=8.0,
        height=10.0,
        obstacles=(
            Obstacle(0.0, 4.5, 5.0, 4.7),
            Obstacle(6.0, 4.5, 8.0, 4.7),
            Obstacle(3.5, 0.0, 3.7, 3.5),
            Obstacle(1.5, 7.0, 3.5, 8.0),
            Obstacle(5.5, 6.5, 7.0, 8.0),
        ),
    ),
    "corridor_v1": MockScene(
        width=50.0,
        height=4.0,
        obstacles=(
            Obstacle(10.0, 0.0, 10.5, 1.5),
            Obstacle(20.0, 2.5, 20.5, 4.0),
            Obstacle(30.0, 0.5, 31.0, 2.0),
            Obstacle(40.0, 2.0, 40.5, 3.5),
        ),
    ),
    "obstacles": MockScene(
        width=10.0,
        height=10.0,
        obstacles=(
            Obstacle(2.0, 2.0, 3.0, 3.0),
            Obstacle(5.0, 1.5, 6.5, 2.5),
            Obstacle(7.0, 5.0, 8.5, 6.5),
            Obstacle(3.0, 6.0, 4.5, 7.5),
            Obstacle(1.0, 8.0, 2.5, 9.5),
            Obstacle(6.0, 7.5, 7.0, 9.0),
            Obstacle(4.5, 4.0, 5.5, 5.0),
        ),
    ),
}


def get_scene(name: str) -> MockScene:
    """Get a scene by name. Falls back to office_v2 for unknown names."""
    return SCENES.get(name, SCENES["office_v2"])
