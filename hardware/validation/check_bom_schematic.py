#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-P-2.0
"""
BOM vs Schematic consistency checker.

Reads hardware/bom/bom_basic.csv and hardware/pcb/robot-platform.kicad_sch,
then verifies every BOM reference designator exists in the schematic.

Handles reference ranges (e.g., "C1-C10", "M1-M4") by expanding them
into individual references.

Exit code: 0 = all match, 1 = discrepancies found.
"""

import csv
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

BOM_FILE = PROJECT_ROOT / "hardware" / "bom" / "bom_basic.csv"
SCHEMATIC_FILE = PROJECT_ROOT / "hardware" / "pcb" / "robot-platform.kicad_sch"

# References for mechanical/off-board components (not on PCB)
MECHANICAL_REFS = {"M1", "M2", "M3", "M4", "W1", "W2", "W3", "W4", "BAT1"}

# References absorbed into other symbols or present with different naming
# BOM "U2" (qty 2) -> schematic "U2a", "U2b"
# BOM "L1" (qty 2) -> inductors inside converter module footprints
REF_ALIASES = {"U2": {"U2a", "U2b"}}
IMPLICIT_REFS = {"L1", "L2"}


def expand_reference_range(ref_field: str) -> set[str]:
    """
    Expand reference ranges into individual references.

    Examples:
        "C1-C10" -> {"C1", "C2", ..., "C10"}
        "M1-M4"  -> {"M1", "M2", "M3", "M4"}
        "U1"     -> {"U1"}
    """
    refs = set()
    # Match ranges like C1-C10, R1-R8, M1-M4, W1-W4
    range_pattern = re.compile(r"^([A-Z]+)(\d+)-\1(\d+)$")
    match = range_pattern.match(ref_field.strip())
    if match:
        prefix = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3))
        for i in range(start, end + 1):
            refs.add(f"{prefix}{i}")
    else:
        # Single reference
        ref_field = ref_field.strip()
        if ref_field:
            refs.add(ref_field)
    return refs


def parse_bom(filepath: Path) -> dict[str, set[str]]:
    """
    Parse BOM CSV and return mapping of reference -> set of individual refs.

    Returns a flat set of all individual reference designators.
    Also returns a dict mapping each BOM row's Reference field to its expanded refs.
    """
    row_refs: dict[str, set[str]] = {}

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "Reference" not in (reader.fieldnames or []):
            print("ERROR: 'Reference' column not found in BOM header")
            sys.exit(1)
        for row in reader:
            ref_field = row.get("Reference", "").strip()
            if ref_field:
                row_refs[ref_field] = expand_reference_range(ref_field)

    return row_refs


def parse_schematic_references(filepath: Path) -> set[str]:
    """Extract all component Reference properties from KiCad schematic."""
    refs = set()
    # Match (property "Reference" "Uxx" ...) patterns
    # Also match (reference "Uxx") in symbol_instances
    prop_pattern = re.compile(r'\(property\s+"Reference"\s+"([^"#]+)"')
    inst_pattern = re.compile(r'\(reference\s+"([^"#]+)"')

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            for match in prop_pattern.finditer(line):
                ref = match.group(1)
                if not ref.startswith("#"):
                    refs.add(ref)
            for match in inst_pattern.finditer(line):
                ref = match.group(1)
                if not ref.startswith("#"):
                    refs.add(ref)

    return refs


def main() -> int:
    """Run BOM vs schematic check."""
    print("=" * 60)
    print("BOM vs Schematic Reference Check")
    print("=" * 60)
    print()

    # Verify files exist
    if not BOM_FILE.exists():
        print(f"ERROR: BOM file not found: {BOM_FILE}")
        return 1
    if not SCHEMATIC_FILE.exists():
        print(f"ERROR: Schematic file not found: {SCHEMATIC_FILE}")
        return 1

    # Parse data
    bom_row_refs = parse_bom(BOM_FILE)
    sch_refs = parse_schematic_references(SCHEMATIC_FILE)

    # Flatten all BOM refs
    all_bom_refs: set[str] = set()
    for expanded in bom_row_refs.values():
        all_bom_refs.update(expanded)

    print(f"BOM file: {BOM_FILE}")
    print(f"  Rows: {len(bom_row_refs)}")
    print(f"  Individual references: {len(all_bom_refs)}")
    print()
    print(f"Schematic file: {SCHEMATIC_FILE}")
    print(f"  Component references: {len(sch_refs)}")
    print()

    # Find discrepancies (excluding known mechanical/implicit refs)
    pcb_bom_refs = all_bom_refs - MECHANICAL_REFS - IMPLICIT_REFS

    # Apply aliases
    expanded_pcb_refs = set()
    for ref in pcb_bom_refs:
        if ref in REF_ALIASES:
            expanded_pcb_refs.update(REF_ALIASES[ref])
        else:
            expanded_pcb_refs.add(ref)

    missing_from_sch = expanded_pcb_refs - sch_refs
    extra_in_sch = sch_refs - expanded_pcb_refs

    has_errors = False

    print("-" * 60)
    print("Results")
    print("-" * 60)
    print()

    if missing_from_sch:
        has_errors = True
        print(f"FAIL: {len(missing_from_sch)} BOM reference(s) missing from schematic:")
        for ref in sorted(missing_from_sch):
            source_row = "unknown"
            for row_field, expanded in bom_row_refs.items():
                if ref in expanded:
                    source_row = row_field
                    break
            print(f"  - {ref} (from BOM row: {source_row})")
        print()
    else:
        skipped = sorted((MECHANICAL_REFS | IMPLICIT_REFS) & all_bom_refs)
        print(
            f"PASS: All {len(expanded_pcb_refs)} PCB BOM references found in schematic."
        )
        if skipped:
            print(f"  (Excluded mechanical/implicit refs: {skipped})")
        print()

    if extra_in_sch:
        print(
            f"INFO: {len(extra_in_sch)} schematic reference(s) not in BOM "
            f"(may be power symbols, test points, DNP, or industrial-only):"
        )
        for ref in sorted(extra_in_sch):
            print(f"  - {ref}")
        print()
    else:
        print("INFO: No extra schematic references beyond BOM.")
        print()

    # Summary
    print("=" * 60)
    if has_errors:
        print("RESULT: FAIL — BOM/schematic mismatch detected")
    else:
        print("RESULT: PASS — BOM and schematic are consistent")
    print("=" * 60)

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
