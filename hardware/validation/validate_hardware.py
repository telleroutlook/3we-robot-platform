#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-P-2.0
"""
Cross-layer hardware validation script.

Validates consistency between:
  - Firmware pin definitions (firmware/config/pin_definitions.h)
  - KiCad schematic net labels (hardware/pcb/robot-platform.kicad_sch)
  - BOM component references (hardware/bom/bom_basic.csv)
  - I2C device addresses

Exit code: 0 = all checks pass, 1 = one or more failures.
"""

import os
import re
import sys
from pathlib import Path

# Resolve project root (two levels up from this script)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

PIN_DEFS_FILE = PROJECT_ROOT / "firmware" / "config" / "pin_definitions.h"
SCHEMATIC_FILE = PROJECT_ROOT / "hardware" / "pcb" / "robot-platform.kicad_sch"
BOM_FILE = PROJECT_ROOT / "hardware" / "bom" / "bom_basic.csv"

# Mapping from firmware #define names to expected schematic net label names.
# The firmware uses MOTOR_FL_IN1 style, schematic uses MOT_FL_IN1 style.
FIRMWARE_TO_NET_MAP = {
    "MOTOR_FL_IN1": "MOT_FL_IN1",
    "MOTOR_FL_IN2": "MOT_FL_IN2",
    "MOTOR_FR_IN1": "MOT_FR_IN1",
    "MOTOR_FR_IN2": "MOT_FR_IN2",
    "MOTOR_RL_IN1": "MOT_RL_IN1",
    "MOTOR_RL_IN2": "MOT_RL_IN2",
    "MOTOR_RR_IN1": "MOT_RR_IN1",
    "MOTOR_RR_IN2": "MOT_RR_IN2",
    "US_TRIG": "US_TRIG",
    "US_ECHO_FRONT": "US_ECHO_FRONT",
    "US_ECHO_BACK": "US_ECHO_BACK",
    "US_ECHO_LEFT": "US_ECHO_LEFT",
    "US_ECHO_RIGHT": "US_ECHO_RIGHT",
    "ENC_FL_A": "ENC_FL_A",
    "ENC_FL_B": "ENC_FL_B",
    "ENC_FR_A": "ENC_FR_A",
    "ENC_FR_B": "ENC_FR_B",
    "ENC_RL_A": "ENC_RL_A",
    "ENC_RL_B": "ENC_RL_B",
    "ENC_RR_A": "ENC_RR_A",
    "ENC_RR_B": "ENC_RR_B",
    "I2C_SDA": "I2C_SDA",
    "I2C_SCL": "I2C_SCL",
    "BATT_ADC_GPIO": "BATT_ADC",
    "ESTOP_GPIO": "ESTOP",
    "SAFETY_RELAY_FB": "SAFETY_RELAY_FB",
    "UROS_TX": "UROS_TX",
    "UROS_RX": "UROS_RX",
    "CAN_MOSI": "CAN_MOSI",
    "CAN_MISO": "CAN_MISO",
    "CAN_SCLK": "CAN_SCLK",
    "CAN_CS": "CAN_CS",
    "CAN_INT": "CAN_INT",
}

# Expected I2C addresses that should appear in the schematic
I2C_ADDRESSES = ["0x28", "0x40", "0x20"]

# BOM references that are mechanical/off-board (not in PCB schematic)
BOM_MECHANICAL_REFS = {
    "M1", "M2", "M3", "M4",      # N20 gear motors (through-hole connectors instead)
    "W1", "W2", "W3", "W4",      # Mecanum wheels (mechanical)
    "BAT1",                        # Battery holder (off-board)
}

# BOM reference mapping (BOM name -> schematic name(s))
BOM_REF_ALIASES = {
    "U2": {"U2a", "U2b"},          # BOM lists qty 2, schematic uses U2a/U2b
}

# BOM references for passive components absorbed into IC symbols or not
# separately instantiated on the schematic (inductors inside converter modules)
BOM_IMPLICIT_REFS = {
    "L1", "L2",                     # Inductors for MT3608/MP1584EN (inside converter footprints)
}


def parse_pin_definitions(filepath: Path) -> dict[str, int]:
    """Parse #define GPIO_NAME NUMBER patterns from pin_definitions.h."""
    pins = {}
    pattern = re.compile(r"^\s*#define\s+(\w+)\s+(\d+)\s*(?://.*)?$")
    with open(filepath, "r") as f:
        for line in f:
            match = pattern.match(line)
            if match:
                name = match.group(1)
                value = int(match.group(2))
                # Only include actual GPIO pin defines (numeric values 0-48)
                if value <= 48:
                    pins[name] = value
    return pins


def parse_schematic_net_labels(filepath: Path) -> set[str]:
    """Parse all net label names from KiCad schematic."""
    labels = set()
    # Match (label "NAME" ...) patterns in KiCad schematic format
    pattern = re.compile(r'\(label\s+"([^"]+)"')
    with open(filepath, "r") as f:
        for line in f:
            for match in pattern.finditer(line):
                labels.add(match.group(1))
    return labels


def parse_schematic_references(filepath: Path) -> set[str]:
    """Parse all component Reference properties from schematic."""
    refs = set()
    # Match (property "Reference" "Uxx" ...) patterns
    pattern = re.compile(r'\(property\s+"Reference"\s+"([^"#]+)"')
    with open(filepath, "r") as f:
        for line in f:
            for match in pattern.finditer(line):
                ref = match.group(1)
                # Skip power symbols starting with #
                if not ref.startswith("#"):
                    refs.add(ref)
    return refs


def parse_bom_references(filepath: Path) -> set[str]:
    """Parse Reference column from BOM CSV, expanding ranges."""
    refs = set()
    with open(filepath, "r") as f:
        lines = f.readlines()

    if not lines:
        return refs

    # Find the Reference column index
    header = lines[0].strip().split(",")
    try:
        ref_idx = header.index("Reference")
    except ValueError:
        print("  ERROR: 'Reference' column not found in BOM header")
        return refs

    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.strip().split(",")
        if len(cols) <= ref_idx:
            continue
        ref_field = cols[ref_idx].strip()
        refs.update(expand_reference_range(ref_field))

    return refs


def expand_reference_range(ref_field: str) -> set[str]:
    """Expand reference ranges like 'C1-C10' or 'M1-M4' into individual refs."""
    refs = set()
    # Match patterns like C1-C10, R1-R8, M1-M4
    range_pattern = re.compile(r"^([A-Z]+)(\d+)-\1(\d+)$")
    match = range_pattern.match(ref_field)
    if match:
        prefix = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3))
        for i in range(start, end + 1):
            refs.add(f"{prefix}{i}")
    else:
        # Single reference or already individual
        refs.add(ref_field)
    return refs


def check_pin_to_net_mapping(
    pin_defines: dict[str, int], net_labels: set[str]
) -> tuple[bool, list[str]]:
    """Verify firmware GPIO defines have corresponding schematic net labels."""
    passed = True
    details = []

    for fw_name, expected_net in FIRMWARE_TO_NET_MAP.items():
        if fw_name not in pin_defines:
            details.append(f"  WARNING: {fw_name} not found in pin_definitions.h")
            continue
        gpio_num = pin_defines[fw_name]
        if expected_net in net_labels:
            details.append(
                f"  OK: {fw_name} (GPIO {gpio_num}) -> net '{expected_net}'"
            )
        else:
            details.append(
                f"  FAIL: {fw_name} (GPIO {gpio_num}) -> "
                f"expected net '{expected_net}' NOT FOUND in schematic"
            )
            passed = False

    return passed, details


def check_bom_in_schematic(
    bom_refs: set[str], sch_refs: set[str]
) -> tuple[bool, list[str]]:
    """Verify BOM component references exist in schematic."""
    passed = True
    details = []

    # Filter out mechanical/off-board refs and implicit refs
    bom_pcb_refs = bom_refs - BOM_MECHANICAL_REFS - BOM_IMPLICIT_REFS

    # Apply aliases: expand BOM refs that map to different schematic names
    expanded_bom = set()
    for ref in bom_pcb_refs:
        if ref in BOM_REF_ALIASES:
            expanded_bom.update(BOM_REF_ALIASES[ref])
        else:
            expanded_bom.add(ref)

    missing = expanded_bom - sch_refs
    extra = sch_refs - expanded_bom

    if BOM_MECHANICAL_REFS & bom_refs:
        skipped = sorted((BOM_MECHANICAL_REFS | BOM_IMPLICIT_REFS) & bom_refs)
        details.append(f"  INFO: Skipped mechanical/off-board/implicit refs: {skipped}")

    if missing:
        passed = False
        details.append(f"  FAIL: BOM refs missing from schematic: {sorted(missing)}")
    else:
        details.append(
            f"  OK: All {len(expanded_bom)} PCB BOM references found in schematic"
        )

    if extra:
        details.append(
            f"  INFO: Schematic refs not in BOM (connectors, extras, etc.): "
            f"{sorted(extra)}"
        )

    return passed, details


def check_i2c_addresses(filepath: Path) -> tuple[bool, list[str]]:
    """Verify expected I2C addresses appear in schematic text."""
    passed = True
    details = []

    with open(filepath, "r") as f:
        content = f.read()

    for addr in I2C_ADDRESSES:
        # Check for the hex address in any form (comments, property values, etc.)
        if addr in content or addr.upper() in content:
            details.append(f"  OK: I2C address {addr} found in schematic")
        else:
            # Also try without 0x prefix
            bare = addr.replace("0x", "").replace("0X", "")
            if bare in content:
                details.append(
                    f"  OK: I2C address {addr} found in schematic (bare form)"
                )
            else:
                details.append(
                    f"  FAIL: I2C address {addr} NOT found in schematic"
                )
                passed = False

    return passed, details


def main() -> int:
    """Run all validation checks."""
    print("=" * 70)
    print("Hardware Validation — Cross-Layer Consistency Check")
    print("=" * 70)
    print()

    all_passed = True

    # Check required files exist
    for filepath, desc in [
        (PIN_DEFS_FILE, "Pin definitions"),
        (SCHEMATIC_FILE, "KiCad schematic"),
        (BOM_FILE, "BOM (basic)"),
    ]:
        if not filepath.exists():
            print(f"ERROR: {desc} not found: {filepath}")
            all_passed = False

    if not all_passed:
        print("\nFailed: required files missing.")
        return 1

    # Parse source data
    pin_defines = parse_pin_definitions(PIN_DEFS_FILE)
    net_labels = parse_schematic_net_labels(SCHEMATIC_FILE)
    sch_refs = parse_schematic_references(SCHEMATIC_FILE)
    bom_refs = parse_bom_references(BOM_FILE)

    print(f"Parsed {len(pin_defines)} GPIO pin defines from firmware")
    print(f"Parsed {len(net_labels)} net labels from schematic")
    print(f"Parsed {len(sch_refs)} component references from schematic")
    print(f"Parsed {len(bom_refs)} component references from BOM")
    print()

    # Check 1: Pin-to-net mapping
    print("-" * 70)
    print("CHECK 1: Firmware GPIO pins -> Schematic net labels")
    print("-" * 70)
    passed, details = check_pin_to_net_mapping(pin_defines, net_labels)
    for d in details:
        print(d)
    status = "PASS" if passed else "FAIL"
    print(f"\n  Result: {status}")
    if not passed:
        all_passed = False
    print()

    # Check 2: BOM references in schematic
    print("-" * 70)
    print("CHECK 2: BOM component references -> Schematic references")
    print("-" * 70)
    passed, details = check_bom_in_schematic(bom_refs, sch_refs)
    for d in details:
        print(d)
    status = "PASS" if passed else "FAIL"
    print(f"\n  Result: {status}")
    if not passed:
        all_passed = False
    print()

    # Check 3: I2C addresses
    print("-" * 70)
    print("CHECK 3: I2C addresses present in schematic")
    print("-" * 70)
    passed, details = check_i2c_addresses(SCHEMATIC_FILE)
    for d in details:
        print(d)
    status = "PASS" if passed else "FAIL"
    print(f"\n  Result: {status}")
    if not passed:
        all_passed = False
    print()

    # Final summary
    print("=" * 70)
    if all_passed:
        print("OVERALL: ALL CHECKS PASSED")
    else:
        print("OVERALL: ONE OR MORE CHECKS FAILED")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
