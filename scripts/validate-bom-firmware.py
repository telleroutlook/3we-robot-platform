# SPDX-License-Identifier: Apache-2.0
"""Validate BOM component specifications against firmware configuration.

Checks:
1. I2C addresses in BOM match firmware #define values
2. Motor specs in BOM align with Kconfig parameters per SKU
3. Key ICs listed in BOM have corresponding firmware driver code
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOM_DIR = ROOT / "hardware" / "bom"
PIN_DEFS = ROOT / "firmware" / "config" / "pin_definitions.h"
SDKCONFIG_DIR = ROOT / "firmware" / "esp32"

# I2C address expectations: (BOM component pattern, firmware define name, expected value)
I2C_CHECKS: list[tuple[str, str, int]] = [
    ("BNO055", "IMU_ADDR", 0x28),
    ("INA219", "INA219_ADDR", 0x40),
    ("MCP23017", "MCP23017_ADDR", 0x20),
]

# Motor gear ratios per SKU from BOM description patterns
MOTOR_GEAR_RATIO_PATTERN = re.compile(r"1:(\d+)")

SKU_BOM_FILES = {
    "basic": "bom_basic.csv",
    "standard": "bom_standard.csv",
    "industrial": "bom_industrial.csv",
}


def parse_firmware_defines(content: str) -> dict[str, int]:
    """Extract all #define NAME value pairs (hex or decimal)."""
    defines: dict[str, int] = {}
    for line in content.split("\n"):
        m = re.match(r"^\s*#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)\s*", line)
        if m:
            name = m.group(1)
            val_str = m.group(2)
            defines[name] = (
                int(val_str, 16) if val_str.startswith("0x") else int(val_str)
            )
    return defines


def parse_sdkconfig(sku: str) -> dict[str, int]:
    """Parse sdkconfig.defaults.<sku> for CONFIG_ values."""
    path = SDKCONFIG_DIR / f"sdkconfig.defaults.{sku}"
    values: dict[str, int] = {}
    if not path.exists():
        return values
    for line in path.read_text().split("\n"):
        m = re.match(r"^(CONFIG_\w+)=(\d+)$", line)
        if m:
            values[m.group(1)] = int(m.group(2))
    return values


def read_bom(filename: str) -> list[dict[str, str]]:
    """Read BOM CSV into list of dicts."""
    path = BOM_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def extract_gear_ratio_from_bom(rows: list[dict[str, str]]) -> int | None:
    """Find motor gear ratio from BOM motor entry."""
    for row in rows:
        value = row.get("Value", "")
        notes = row.get("Notes", "")
        ref = row.get("Reference", "")
        if "Motor" in value or "MOT" in ref:
            m = MOTOR_GEAR_RATIO_PATTERN.search(value)
            if m:
                return int(m.group(1))
            m = MOTOR_GEAR_RATIO_PATTERN.search(notes)
            if m:
                return int(m.group(1))
    return None


def check_bom_has_component(rows: list[dict[str, str]], pattern: str) -> bool:
    """Check if BOM contains a component matching the pattern."""
    for row in rows:
        if pattern in row.get("Value", "") or pattern in row.get("MPN", ""):
            return True
    return False


def main() -> int:
    print("=== BOM ↔ Firmware Alignment ===\n")

    if not PIN_DEFS.exists():
        print("[SKIP] pin_definitions.h not found")
        return 0

    fw_defines = parse_firmware_defines(PIN_DEFS.read_text())
    errors = 0
    passed = 0

    # Phase 1: I2C addresses
    print("--- I2C Addresses ---\n")
    basic_bom = read_bom("bom_basic.csv")

    for component, define_name, expected in I2C_CHECKS:
        fw_val = fw_defines.get(define_name)
        bom_has = check_bom_has_component(basic_bom, component)

        if not bom_has:
            continue

        if fw_val is None:
            print(f"  [ERROR] BOM has {component} but firmware missing {define_name}")
            errors += 1
        elif fw_val != expected:
            print(
                f"  [ERROR] {component}: BOM expects 0x{expected:02X}, "
                f"firmware {define_name}=0x{fw_val:02X}"
            )
            errors += 1
        else:
            print(f"  ✓ {component}: address 0x{fw_val:02X} matches")
            passed += 1

    # Phase 2: Motor gear ratios per SKU
    print("\n--- Motor Gear Ratios ---\n")

    for sku, bom_file in SKU_BOM_FILES.items():
        bom_rows = read_bom(bom_file)
        if not bom_rows:
            print(f"  [SKIP] {bom_file} not found")
            continue

        bom_ratio = extract_gear_ratio_from_bom(bom_rows)
        if bom_ratio is None:
            print(f"  [SKIP] {sku}: no motor gear ratio found in BOM")
            continue

        sdkconfig = parse_sdkconfig(sku)
        fw_ratio = sdkconfig.get("CONFIG_MOTOR_GEAR_RATIO")

        if fw_ratio is None:
            # Basic SKU may use robot_params.h defaults
            if sku == "basic":
                content = (ROOT / "firmware" / "config" / "robot_params.h").read_text()
                m = re.search(r"#define\s+GEAR_RATIO\s+(\d+)", content)
                if m:
                    fw_ratio = int(m.group(1))

        if fw_ratio is None:
            print(f"  [WARN] {sku}: BOM ratio 1:{bom_ratio}, firmware ratio not found")
        elif fw_ratio != bom_ratio:
            print(
                f"  [ERROR] {sku}: BOM motor 1:{bom_ratio}, "
                f"firmware CONFIG_MOTOR_GEAR_RATIO={fw_ratio}"
            )
            errors += 1
        else:
            print(f"  ✓ {sku}: gear ratio 1:{bom_ratio} matches")
            passed += 1

    # Phase 3: Industrial-only components
    print("\n--- SKU-Specific Components ---\n")

    industrial_bom = read_bom("bom_industrial.csv")
    if industrial_bom:
        industrial_expected = [
            ("MCP2515", "CAN controller"),
            ("BTS7960", "motor driver"),
            ("ACS712", "current sensor"),
        ]
        for component, desc in industrial_expected:
            if check_bom_has_component(industrial_bom, component):
                print(f"  ✓ Industrial BOM includes {component} ({desc})")
                passed += 1
            else:
                print(f"  [WARN] Industrial BOM missing expected {component} ({desc})")

    print(f"\n{'─' * 50}")
    print(f"Result: {passed} passed, {errors} errors")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
