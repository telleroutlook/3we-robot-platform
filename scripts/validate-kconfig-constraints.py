# SPDX-License-Identifier: Apache-2.0
"""Validate Kconfig constraints across sdkconfig overlay files.

Ensures:
1. Exactly one SKU is selected per sdkconfig overlay
2. SKU-gated features are only enabled in compatible SKUs
3. Required parameters are present when their feature is enabled
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SDKCONFIG_DIR = ROOT / "firmware" / "esp32"

SKU_FLAGS = [
    "CONFIG_ROBOT_SKU_BASIC",
    "CONFIG_ROBOT_SKU_STANDARD",
    "CONFIG_ROBOT_SKU_INDUSTRIAL",
]

# Additive overlays (applied on top of a SKU config, no standalone SKU flag expected)
ADDITIVE_OVERLAYS = {"competition", "production"}

# Rules: (feature_flag, allowed_skus, description)
FEATURE_SKU_RULES: list[tuple[str, set[str], str]] = [
    (
        "CONFIG_ROBOT_DOCKING_ENABLED",
        {"CONFIG_ROBOT_SKU_STANDARD", "CONFIG_ROBOT_SKU_INDUSTRIAL"},
        "Docking requires Standard or Industrial SKU (needs Pi 5 compute)",
    ),
    (
        "CONFIG_CURRENT_SENSE_ENABLED",
        {"CONFIG_ROBOT_SKU_INDUSTRIAL"},
        "Current sensing only available on Industrial SKU (ACS712 hardware)",
    ),
    (
        "CONFIG_ROBOT_DUAL_BATTERY",
        {"CONFIG_ROBOT_SKU_STANDARD", "CONFIG_ROBOT_SKU_INDUSTRIAL"},
        "Dual battery requires Standard or Industrial (PCB routing)",
    ),
    (
        "CONFIG_ROBOT_PROFILE_COMPETITION",
        {"CONFIG_ROBOT_SKU_STANDARD", "CONFIG_ROBOT_SKU_INDUSTRIAL"},
        "Competition profile requires Standard or Industrial (Pi 5 for AI)",
    ),
]

# Required parameter groups: (gate_flag, required_params[])
REQUIRED_PARAMS: list[tuple[str, list[str]]] = [
    (
        "CONFIG_CHASSIS_WHEEL_RADIUS_MM_X10",
        [
            "CONFIG_CHASSIS_TRACK_WIDTH_MM",
            "CONFIG_CHASSIS_WHEELBASE_MM",
        ],
    ),
    (
        "CONFIG_MOTOR_GEAR_RATIO",
        [
            "CONFIG_MOTOR_ENCODER_PPR",
            "CONFIG_MOTOR_MAX_RPM",
            "CONFIG_MOTOR_PWM_FREQ_HZ",
        ],
    ),
]


def parse_sdkconfig(path: Path) -> dict[str, str]:
    """Parse sdkconfig file into key=value dict (values as strings)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(CONFIG_\w+)=(.+)$", line)
        if m:
            values[m.group(1)] = m.group(2)
    return values


def main() -> int:
    print("=== Kconfig Constraint Validation ===\n")

    overlay_files = sorted(SDKCONFIG_DIR.glob("sdkconfig.defaults.*"))
    if not overlay_files:
        print("[SKIP] No sdkconfig overlay files found")
        return 0

    errors = 0
    passed = 0

    for overlay in overlay_files:
        sku_name = overlay.name.replace("sdkconfig.defaults.", "")
        config = parse_sdkconfig(overlay)
        issues: list[str] = []
        is_additive = sku_name in ADDITIVE_OVERLAYS

        # Rule 1: Exactly one SKU flag (only for standalone SKU configs)
        active_skus = [s for s in SKU_FLAGS if config.get(s) == "y"]
        if not is_additive:
            if len(active_skus) == 0:
                issues.append("No SKU flag set (need exactly one CONFIG_ROBOT_SKU_*=y)")
            elif len(active_skus) > 1:
                issues.append(
                    f"Multiple SKU flags: {', '.join(active_skus)} (need exactly one)"
                )

        active_sku = active_skus[0] if len(active_skus) == 1 else None

        # Rule 2: Feature-SKU compatibility
        if active_sku:
            for feature, allowed, reason in FEATURE_SKU_RULES:
                if config.get(feature) == "y" and active_sku not in allowed:
                    issues.append(
                        f"{feature}=y not allowed with {active_sku}: {reason}"
                    )

        # Rule 3: Required parameter groups
        for gate, required in REQUIRED_PARAMS:
            if gate in config:
                for param in required:
                    if param not in config:
                        issues.append(
                            f"{gate} is set but required companion {param} is missing"
                        )

        if issues:
            print(f"✗ {overlay.name}:")
            for issue in issues:
                print(f"  [ERROR] {issue}")
                errors += 1
        else:
            params = len(config)
            if is_additive:
                print(f"✓ {overlay.name} — additive overlay, {params} params, OK")
            else:
                sku_label = (
                    active_sku.replace("CONFIG_ROBOT_SKU_", "").lower()
                    if active_sku
                    else "?"
                )
                print(
                    f"✓ {overlay.name} — SKU={sku_label}, {params} params, constraints OK"
                )
            passed += 1

    print(f"\n{'─' * 50}")
    print(f"Result: {passed} passed, {errors} errors")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
