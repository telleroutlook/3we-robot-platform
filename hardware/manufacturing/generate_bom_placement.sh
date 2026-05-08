#!/bin/bash
# SPDX-License-Identifier: CERN-OHL-P-2.0
#
# Generate BOM and component placement (centroid) files for SMT assembly.
# Output format: CSV compatible with JLCPCB assembly service.
#
# NOTE: Make this file executable with: chmod +x generate_bom_placement.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCH_FILE="$PROJECT_ROOT/hardware/pcb/robot-platform.kicad_sch"
PCB_FILE="$PROJECT_ROOT/hardware/pcb/robot-platform.kicad_pcb"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Verify kicad-cli is available
if ! command -v kicad-cli &> /dev/null; then
    echo "ERROR: kicad-cli not found. Install KiCad 8+ and ensure kicad-cli is in PATH."
    exit 1
fi

# Verify source files exist
if [ ! -f "$SCH_FILE" ]; then
    echo "ERROR: Schematic file not found: $SCH_FILE"
    exit 1
fi

if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=== Generating BOM ==="
echo "Schematic: $SCH_FILE"
echo "Output:    $OUTPUT_DIR/bom.csv"
echo ""

# Export BOM from schematic
# JLCPCB format: Comment, Designator, Footprint, LCSC Part Number
kicad-cli sch export bom \
    --output "$OUTPUT_DIR/bom.csv" \
    --fields "Reference,Value,Footprint,MPN" \
    --labels "Designator,Comment,Footprint,LCSC Part #" \
    --group-by "Value,Footprint" \
    --sort-field "Reference" \
    "$SCH_FILE"

echo "BOM generated: $OUTPUT_DIR/bom.csv"
echo ""

echo "=== Generating Component Placement (CPL) ==="
echo "PCB file: $PCB_FILE"
echo "Output:   $OUTPUT_DIR/positions.csv"
echo ""

# Export component placement file (centroid/pick-and-place)
# JLCPCB format: Designator, Mid X, Mid Y, Layer, Rotation
kicad-cli pcb export pos \
    --output "$OUTPUT_DIR/positions.csv" \
    --format csv \
    --units mm \
    --side front \
    --use-drill-file-origin \
    "$PCB_FILE"

echo "Placement file generated: $OUTPUT_DIR/positions.csv"
echo ""

echo "=== Generation complete ==="
echo ""
echo "Output files:"
ls -la "$OUTPUT_DIR/bom.csv" "$OUTPUT_DIR/positions.csv" 2>/dev/null
echo ""
echo "Upload these files to JLCPCB assembly service:"
echo "  1. bom.csv       — Bill of Materials"
echo "  2. positions.csv — Component Placement (CPL/Centroid)"
echo ""
echo "IMPORTANT: Verify component rotations match JLCPCB library orientations."
echo "           Some components may need rotation offset adjustments."
