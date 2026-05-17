# SPDX-License-Identifier: Apache-2.0
"""HardwareProfile Protocol and loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class HardwareProfile(Protocol):
    """Protocol defining the hardware characteristics of a robot platform.

    Implementations describe the physical robot: wheel type, dimensions,
    sensor suite, and kinematic limits. The Robot class uses this to
    adapt commands and interpret sensor data correctly.
    """

    @property
    def name(self) -> str: ...

    @property
    def wheel_type(self) -> str: ...

    @property
    def wheel_separation(self) -> float: ...

    @property
    def wheel_radius(self) -> float: ...

    @property
    def max_linear_velocity(self) -> float: ...

    @property
    def max_angular_velocity(self) -> float: ...

    @property
    def sensors(self) -> list[str]: ...

    @property
    def weight_kg(self) -> float: ...


@dataclass(frozen=True)
class HardwareProfileData:
    """Concrete implementation of HardwareProfile from config data."""

    name: str = "3we_standard_v2"
    wheel_type: str = "mecanum"
    wheel_separation: float = 0.24
    wheel_radius: float = 0.0325
    max_linear_velocity: float = 0.5
    max_angular_velocity: float = 2.0
    sensors: list[str] = field(
        default_factory=lambda: ["lidar_ld06", "imu_bno055", "camera_ov5647", "depth_oak_d_lite"]
    )
    weight_kg: float = 3.5


_BUILTIN_PROFILES: dict[str, HardwareProfileData] = {
    "3we_standard_v2": HardwareProfileData(),
    "agilex_scout": HardwareProfileData(
        name="agilex_scout",
        wheel_type="differential",
        wheel_separation=0.58,
        wheel_radius=0.165,
        max_linear_velocity=1.5,
        max_angular_velocity=3.0,
        sensors=["lidar_velodyne_vlp16", "imu_xsens", "camera_realsense_d435"],
        weight_kg=65.0,
    ),
    "turtlebot4": HardwareProfileData(
        name="turtlebot4",
        wheel_type="differential",
        wheel_separation=0.287,
        wheel_radius=0.038,
        max_linear_velocity=0.31,
        max_angular_velocity=1.9,
        sensors=["lidar_rplidar_a1", "imu_create3", "camera_oakd_pro"],
        weight_kg=3.9,
    ),
    "unitree_go2": HardwareProfileData(
        name="unitree_go2",
        wheel_type="legged",
        wheel_separation=0.0,
        wheel_radius=0.0,
        max_linear_velocity=2.5,
        max_angular_velocity=4.0,
        sensors=["lidar_livox_mid360", "imu_internal", "camera_stereo_front"],
        weight_kg=15.0,
    ),
}


def load_hardware_profile(name: str) -> HardwareProfileData:
    """Load a hardware profile by name.

    Supports built-in profiles, external profiles from ~/.threewe/profiles/,
    and custom YAML files.

    Args:
        name: Profile name (e.g., "3we_standard_v2", "agilex_scout")
              or path to a YAML file.

    Returns:
        HardwareProfileData instance.
    """
    if name in _BUILTIN_PROFILES:
        return _BUILTIN_PROFILES[name]

    path = Path(name)
    if path.exists() and path.suffix in (".yaml", ".yml"):
        return _load_from_yaml(path)

    configs_dir = Path(__file__).parent.parent.parent.parent / "configs"
    yaml_path = configs_dir / f"{name}.yaml"
    if yaml_path.exists():
        return _load_from_yaml(yaml_path)

    from threewe.hal.discovery import discover_external_profiles

    external = discover_external_profiles()
    if name in external:
        return external[name]

    available = ", ".join(sorted(_BUILTIN_PROFILES.keys()))
    raise ValueError(f"Unknown hardware profile '{name}'. Available: {available}")


def _load_from_yaml(path: Path) -> HardwareProfileData:
    """Load hardware profile from a YAML file."""
    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML is required to load hardware profiles from YAML. "
            "Install with: pip install pyyaml"
        ) from e

    with open(path) as f:
        data = yaml.safe_load(f)

    return HardwareProfileData(
        name=data.get("name", path.stem),
        wheel_type=data.get("wheel_type", "differential"),
        wheel_separation=data.get("wheel_separation", 0.3),
        wheel_radius=data.get("wheel_radius", 0.05),
        max_linear_velocity=data.get("max_linear_velocity", 0.5),
        max_angular_velocity=data.get("max_angular_velocity", 2.0),
        sensors=data.get("sensors", []),
        weight_kg=data.get("weight_kg", 5.0),
    )
