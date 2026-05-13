# SPDX-License-Identifier: Apache-2.0
"""HAL profile discovery — finds external hardware profiles.

Scans ~/.threewe/profiles/ for user-installed YAML profiles,
enabling third-party hardware support without modifying the SDK.
"""

from __future__ import annotations

from pathlib import Path

from threewe.hal.interface import _BUILTIN_PROFILES, HardwareProfileData, _load_from_yaml

_EXTERNAL_PROFILES_DIR = Path.home() / ".threewe" / "profiles"


def discover_external_profiles() -> dict[str, HardwareProfileData]:
    """Scan ~/.threewe/profiles/ for YAML hardware profiles.

    Returns:
        Dict mapping profile names to loaded HardwareProfileData.
        Empty dict if the directory doesn't exist or contains no valid profiles.
    """
    profiles: dict[str, HardwareProfileData] = {}

    if not _EXTERNAL_PROFILES_DIR.is_dir():
        return profiles

    for yaml_file in sorted(_EXTERNAL_PROFILES_DIR.glob("*.yaml")):
        try:
            profile = _load_from_yaml(yaml_file)
            profiles[profile.name] = profile
        except Exception:
            continue

    for yml_file in sorted(_EXTERNAL_PROFILES_DIR.glob("*.yml")):
        try:
            profile = _load_from_yaml(yml_file)
            if profile.name not in profiles:
                profiles[profile.name] = profile
        except Exception:
            continue

    return profiles


def list_all_profiles() -> dict[str, HardwareProfileData]:
    """List all available profiles — builtin + external.

    Returns:
        Dict of all available hardware profiles. External profiles
        with the same name as builtins will override the builtin.
    """
    all_profiles = dict(_BUILTIN_PROFILES)
    external = discover_external_profiles()
    all_profiles.update(external)
    return all_profiles
