# SPDX-License-Identifier: Apache-2.0
"""Scene registry — loads scene metadata from bundled YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_SCENES_DIR = Path(__file__).parent

_BUILTIN_SCENES = ("office_v2", "apartment_v1", "corridor_v1")


@dataclass(frozen=True)
class Pose2D:
    """A 2D pose (x, y, theta)."""

    x: float
    y: float
    theta: float = 0.0


@dataclass(frozen=True)
class SceneMetadata:
    """Metadata for a simulation scene including evaluation poses."""

    name: str
    area: str
    difficulty: str
    description: str
    start_poses: tuple[Pose2D, ...]
    goal_poses: tuple[Pose2D, ...]


def list_scenes() -> list[str]:
    """Return names of all available built-in scenes."""
    return list(_BUILTIN_SCENES)


def load_scene(name_or_path: str) -> SceneMetadata:
    """Load a scene by built-in name or path to a metadata.yaml file.

    Args:
        name_or_path: A built-in scene name (e.g. 'office_v2') or
            path to a directory containing metadata.yaml.

    Returns:
        SceneMetadata with loaded poses.

    Raises:
        ValueError: If the scene name is unknown.
        FileNotFoundError: If a path is given but files are missing.
    """
    yaml = _import_yaml()

    path = Path(name_or_path)
    if path.is_dir():
        scene_dir = path
    elif name_or_path in _BUILTIN_SCENES:
        scene_dir = _SCENES_DIR / name_or_path
    else:
        raise ValueError(f"Unknown scene: '{name_or_path}'. Available: {list(_BUILTIN_SCENES)}")

    metadata_file = scene_dir / "metadata.yaml"
    start_file = scene_dir / "start_poses.yaml"
    goal_file = scene_dir / "goal_poses.yaml"

    for f in (metadata_file, start_file, goal_file):
        if not f.exists():
            raise FileNotFoundError(f"Required scene file not found: {f}")

    meta = yaml.safe_load(metadata_file.read_text())
    starts_raw = yaml.safe_load(start_file.read_text())
    goals_raw = yaml.safe_load(goal_file.read_text())

    start_poses = tuple(
        Pose2D(x=p["x"], y=p["y"], theta=p.get("theta", 0.0)) for p in starts_raw["poses"]
    )
    goal_poses = tuple(
        Pose2D(x=p["x"], y=p["y"], theta=p.get("theta", 0.0)) for p in goals_raw["poses"]
    )

    return SceneMetadata(
        name=meta["name"],
        area=meta["area"],
        difficulty=meta["difficulty"],
        description=meta["description"],
        start_poses=start_poses,
        goal_poses=goal_poses,
    )


def _import_yaml():
    """Lazily import PyYAML."""
    try:
        import yaml

        return yaml
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for scene loading. Install with: pip install pyyaml"
        ) from exc
