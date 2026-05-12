# SPDX-License-Identifier: Apache-2.0
"""Validate GPIO pin assignments for conflicts across SKU configurations.

Parses firmware/config/pin_definitions.h and detects:
1. Two different signals sharing the same GPIO in the same SKU build
2. Undocumented pin conflicts (shares without explanatory comments)

Known valid shares are declared explicitly — new accidental conflicts trigger errors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

ROOT = Path(__file__).resolve().parent.parent
PIN_DEFS = ROOT / "firmware" / "config" / "pin_definitions.h"


@dataclass
class PinAssignment:
    name: str
    gpio: int
    guard: str  # empty string = unconditional


@dataclass
class KnownShare:
    gpio: int
    signals: frozenset[str]
    reason: str


KNOWN_SHARES: list[KnownShare] = [
    KnownShare(
        gpio=9,
        signals=frozenset({"US_ECHO_LEFT", "CHARGE_ADC_GPIO", "CAN_INT"}),
        reason="Docking reuses US left pin; Industrial reuses for CAN",
    ),
    KnownShare(
        gpio=5,
        signals=frozenset({"ENC_FL_A", "CURRENT_SENSE_FL_GPIO"}),
        reason="Industrial uses SPI encoder, freeing GPIO for current sense",
    ),
    KnownShare(
        gpio=6,
        signals=frozenset({"ENC_FL_B", "CURRENT_SENSE_FR_GPIO"}),
        reason="Industrial uses SPI encoder, freeing GPIO for current sense",
    ),
    KnownShare(
        gpio=7,
        signals=frozenset({"ENC_FR_A", "CURRENT_SENSE_RL_GPIO"}),
        reason="Industrial uses SPI encoder, freeing GPIO for current sense",
    ),
    KnownShare(
        gpio=8,
        signals=frozenset({"ENC_RR_A", "CURRENT_SENSE_RR_GPIO"}),
        reason="Industrial uses SPI encoder, freeing GPIO for current sense",
    ),
    KnownShare(
        gpio=11,
        signals=frozenset({"US_ECHO_FRONT", "CAN_MOSI"}),
        reason="Industrial omits ultrasonic array, reuses for CAN SPI",
    ),
    KnownShare(
        gpio=10,
        signals=frozenset({"US_ECHO_BACK", "CAN_MISO"}),
        reason="Industrial omits ultrasonic array, reuses for CAN SPI",
    ),
    KnownShare(
        gpio=12,
        signals=frozenset({"US_TRIG", "CAN_SCLK"}),
        reason="Industrial omits ultrasonic array, reuses for CAN SPI",
    ),
    KnownShare(
        gpio=18,
        signals=frozenset({"US_ECHO_RIGHT", "CAN_CS"}),
        reason="Industrial omits ultrasonic array, reuses for CAN SPI",
    ),
    KnownShare(
        gpio=4,
        signals=frozenset({"ENC_RR_B", "BATT_PACK2_ADC_GPIO"}),
        reason="Dual-battery mode reroutes encoder via PCB jumper",
    ),
]


def parse_pin_definitions(content: str) -> list[PinAssignment]:
    """Extract all GPIO pin #define assignments with their #ifdef guards."""
    assignments: list[PinAssignment] = []
    current_guard = ""
    guard_stack: list[str] = []

    for line in content.split("\n"):
        stripped = line.strip()

        # Track #ifdef / #endif nesting
        ifdef_m = re.match(r"^#ifdef\s+(\w+)", stripped)
        if ifdef_m:
            guard_stack.append(ifdef_m.group(1))
            current_guard = guard_stack[-1]
            continue

        if stripped == "#endif" or stripped.startswith("#endif "):
            if guard_stack:
                guard_stack.pop()
            current_guard = guard_stack[-1] if guard_stack else ""
            continue

        # Match #define NAME <number>
        define_m = re.match(r"^#define\s+(\w+)\s+(\d+)\s*", stripped)
        if define_m:
            name = define_m.group(1)
            value = int(define_m.group(2))
            # Filter to GPIO pin assignments (not channel numbers, addresses, frequencies, etc.)
            if _is_gpio_pin(name, value):
                assignments.append(
                    PinAssignment(name=name, gpio=value, guard=current_guard)
                )

    return assignments


def _is_gpio_pin(name: str, value: int) -> bool:
    """Heuristic: is this #define a GPIO pin assignment?"""
    if value > 48 or value < 0:
        return False
    # Exclude non-GPIO defines
    exclude_patterns = [
        "_CH",  # LEDC channels
        "_ADDR",  # I2C addresses
        "_FREQ",  # Frequencies
        "_NUM",  # UART numbers
        "_BAUD",  # Baud rates
        "_ATTEN",  # ADC attenuation
        "_CHANNEL",  # ADC channels
        "_BIT",  # Bit positions
        "_EN_ACTIVE",  # Flags
        "_HOST",  # SPI hosts
    ]
    for pat in exclude_patterns:
        if pat in name:
            return False
    # Include known GPIO naming patterns
    gpio_patterns = [
        "GPIO",
        "TRIG",
        "ECHO",
        "ENC_",
        "MOTOR_",
        "SDA",
        "SCL",
        "TX",
        "RX",
        "MOSI",
        "MISO",
        "SCLK",
        "CS",
        "INT",
        "RELAY",
        "ESTOP",
        "WDT",
        "CURRENT_SENSE",
        "CHARGE",
        "BATT_ADC_GPIO",
        "BATT_PACK2",
    ]
    return any(pat in name for pat in gpio_patterns)


@dataclass
class SkuConfig:
    name: str
    guards: set[str] = field(default_factory=set)


SKU_CONFIGS: list[SkuConfig] = [
    SkuConfig(name="basic", guards=set()),
    SkuConfig(
        name="standard",
        guards={"CONFIG_ROBOT_DOCKING_ENABLED"},
    ),
    SkuConfig(
        name="industrial",
        guards={
            "CONFIG_ROBOT_SKU_INDUSTRIAL",
            "CONFIG_CURRENT_SENSE_ENABLED",
        },
    ),
]


def pins_active_for_sku(
    assignments: list[PinAssignment], sku: SkuConfig
) -> list[PinAssignment]:
    """Return pins active for a given SKU configuration."""
    active: list[PinAssignment] = []
    for pin in assignments:
        if pin.guard == "":
            active.append(pin)
        elif pin.guard in sku.guards:
            active.append(pin)
    return active


def is_known_share(gpio: int, name_a: str, name_b: str) -> bool:
    """Check if two signals sharing a GPIO is a known/documented conflict."""
    for share in KNOWN_SHARES:
        if share.gpio == gpio and name_a in share.signals and name_b in share.signals:
            return True
    return False


def main() -> int:
    if not PIN_DEFS.exists():
        print("[SKIP] pin_definitions.h not found")
        return 0

    content = PIN_DEFS.read_text()
    assignments = parse_pin_definitions(content)

    print("=== GPIO Pin Conflict Detection ===\n")
    print(f"Parsed {len(assignments)} GPIO pin assignments\n")

    errors = 0
    passed = 0

    for sku in SKU_CONFIGS:
        active = pins_active_for_sku(assignments, sku)
        gpio_map: dict[int, list[str]] = {}
        for pin in active:
            gpio_map.setdefault(pin.gpio, []).append(pin.name)

        conflicts = {g: names for g, names in gpio_map.items() if len(names) > 1}
        unknown_conflicts: list[tuple[int, list[str]]] = []

        for gpio, names in conflicts.items():
            all_known = True
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    if not is_known_share(gpio, names[i], names[j]):
                        all_known = False
                        break
            if not all_known:
                unknown_conflicts.append((gpio, names))

        if unknown_conflicts:
            print(f"✗ {sku.name} SKU — {len(unknown_conflicts)} unknown conflict(s):")
            for gpio, names in unknown_conflicts:
                print(f"  [ERROR] GPIO {gpio} shared by: {', '.join(names)}")
                errors += 1
        else:
            known_count = len(conflicts)
            print(
                f"✓ {sku.name} SKU — {len(active)} pins active, "
                f"{known_count} known shares (documented)"
            )
            passed += 1

    print(f"\n{'─' * 50}")
    print(f"Result: {passed} passed, {errors} errors")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
