#!/bin/bash
# SPDX-License-Identifier: CERN-OHL-P-2.0
#
# Generate Gerber and drill files for PCB fabrication using kicad-cli (KiCad 8+).
# Output: hardware/manufacturing/output/
#
# NOTE: Make this file executable with: chmod +x generate_gerbers.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PCB_FILE="$PROJECT_ROOT/hardware/pcb/robot-platform.kicad_pcb"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Verify kicad-cli is available
if ! command -v kicad-cli &> /dev/null; then
    echo "ERROR: kicad-cli not found. Install KiCad 8+ and ensure kicad-cli is in PATH."
    exit 1
fi

# Verify PCB file exists
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=== Generating Gerber files ==="
echo "PCB file: $PCB_FILE"
echo "Output:   $OUTPUT_DIR"
echo ""

# Export Gerber files for all required layers
kicad-cli pcb export gerbers \
    --output "$OUTPUT_DIR/" \
    --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts" \
    --subtract-soldermask \
    --no-x2 \
    --use-drill-file-origin \
    "$PCB_FILE"

echo ""
echo "=== Generating Excellon drill file ==="

# Export Excellon drill file
kicad-cli pcb export drill \
    --output "$OUTPUT_DIR/" \
    --format excellon \
    --drill-origin plot \
    --excellon-units mm \
    --excellon-zeros-format decimal \
    --generate-map \
    --map-format gerberx2 \
    "$PCB_FILE"

echo ""
echo "=== Generation complete ==="
echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR/"
echo ""
echo "File summary:"
echo "  Gerber layers: $(find "$OUTPUT_DIR" -name '*.gbr' | wc -l | tr -d ' ')"
echo "  Drill files:   $(find "$OUTPUT_DIR" -name '*.drl' -o -name '*.xln' | wc -l | tr -d ' ')"
echo "  Map files:     $(find "$OUTPUT_DIR" -name '*-drl_map*' | wc -l | tr -d ' ')"
echo ""
echo "Ready to upload to JLCPCB/PCBWay for fabrication."
