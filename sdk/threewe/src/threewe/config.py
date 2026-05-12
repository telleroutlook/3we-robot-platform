# SPDX-License-Identifier: Apache-2.0
"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    max_linear_velocity: float = 0.5
    max_angular_velocity: float = 1.0
    safety_distance: float = 0.15


@dataclass(frozen=True, slots=True)
class NavigationConfig:
    planner: str = "navfn"
    controller: str = "dwb"
    goal_tolerance: float = 0.1


@dataclass(frozen=True, slots=True)
class APIConfig:
    image_size: tuple[int, int] = (640, 480)
    lidar_points: int = 360
    control_frequency: int = 50


@dataclass(frozen=True, slots=True)
class HardwareConfig:
    platform: str = "3we_standard_v2"
    wheels: str = "mecanum_65mm"
    lidar: str = "ld06"
    camera: str = "fisheye_1080p"
    imu: str = "bno055"


@dataclass(slots=True)
class RobotConfig:
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    navigation: NavigationConfig = field(default_factory=NavigationConfig)
    api: APIConfig = field(default_factory=APIConfig)


_BUILTIN_CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"


def load_config(name: str = "standard_v2") -> RobotConfig:
    """Load a robot configuration by name.

    Searches in order:
    1. Absolute/relative path if name contains a path separator
    2. Built-in configs directory (sdk/threewe/configs/)
    3. Current working directory
    """
    path = _resolve_config_path(name)
    if path is None:
        return RobotConfig()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    return _parse_config(raw)


def _resolve_config_path(name: str) -> Path | None:
    candidate = Path(name)
    if candidate.is_file():
        return candidate

    if not name.endswith((".yaml", ".yml")):
        name = f"{name}.yaml"

    for directory in [_BUILTIN_CONFIGS_DIR, Path.cwd()]:
        path = directory / name
        if path.is_file():
            return path

    return None


def _parse_config(raw: dict) -> RobotConfig:
    hw = raw.get("hardware", {})
    lim = raw.get("limits", {})
    nav = raw.get("navigation", {})
    api = raw.get("api", {})

    image_size = api.get("image_size", [640, 480])
    if isinstance(image_size, list):
        image_size = tuple(image_size)

    return RobotConfig(
        hardware=HardwareConfig(
            platform=hw.get("platform", "3we_standard_v2"),
            wheels=hw.get("wheels", "mecanum_65mm"),
            lidar=hw.get("lidar", "ld06"),
            camera=hw.get("camera", "fisheye_1080p"),
            imu=hw.get("imu", "bno055"),
        ),
        limits=LimitsConfig(
            max_linear_velocity=lim.get("max_linear_velocity", 0.5),
            max_angular_velocity=lim.get("max_angular_velocity", 1.0),
            safety_distance=lim.get("safety_distance", 0.15),
        ),
        navigation=NavigationConfig(
            planner=nav.get("planner", "navfn"),
            controller=nav.get("controller", "dwb"),
            goal_tolerance=nav.get("goal_tolerance", 0.1),
        ),
        api=APIConfig(
            image_size=image_size,
            lidar_points=api.get("lidar_points", 360),
            control_frequency=api.get("control_frequency", 50),
        ),
    )
