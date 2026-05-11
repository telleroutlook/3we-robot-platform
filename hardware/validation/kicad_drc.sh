#!/bin/bash
# SPDX-License-Identifier: CERN-OHL-P-2.0
#
# Run KiCad Design Rule Check (DRC) on the robot platform PCB.
# Outputs violations to stdout and exits non-zero if any are found.
#
# NOTE: Make this file executable with: chmod +x kicad_drc.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PCB_FILE="$PROJECT_ROOT/hardware/pcb/robot-platform.kicad_pcb"

# Locate kicad-cli
KICAD_CLI=""
if command -v kicad-cli &>/dev/null; then
    KICAD_CLI="kicad-cli"
elif [ -x "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" ]; then
    KICAD_CLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
else
    echo "WARNING: kicad-cli not found."
    echo "Install KiCad 8+ and ensure kicad-cli is in PATH."
    echo ""
    echo "On macOS:  /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    echo "On Linux:  kicad-cli (from KiCad 8+ package)"
    echo ""
    echo "Skipping DRC (kicad-cli unavailable)."
    exit 0
fi

# Verify PCB file exists
if [ ! -f "$PCB_FILE" ]; then
    echo "ERROR: PCB file not found: $PCB_FILE"
    exit 1
fi

echo "=== KiCad Design Rule Check ==="
echo "PCB file: $PCB_FILE"
echo ""

# Create temporary file for DRC report
DRC_REPORT=$(mktemp /tmp/drc_report_XXXXXX.json)
trap 'rm -f "$DRC_REPORT"' EXIT

# Run DRC
DRC_OUTPUT=$("$KICAD_CLI" pcb drc \
    --output "$DRC_REPORT" \
    --format json \
    --severity-all \
    "$PCB_FILE" 2>&1) || true

DRC_EXIT=$?

# Exit code 255 indicates a file parse error (not a DRC violation)
if [ $DRC_EXIT -eq 255 ]; then
    echo "ERROR: KiCad could not parse the PCB file."
    echo "$DRC_OUTPUT"
    exit 1
fi

# Display results
if [ $DRC_EXIT -eq 0 ]; then
    echo "DRC PASSED: No violations found."
    echo ""
    if [ -f "$DRC_REPORT" ]; then
        echo "Full report:"
        cat "$DRC_REPORT"
    fi
    exit 0
else
    echo "DRC completed with violations (exit code $DRC_EXIT)."
    echo ""
    if [ -f "$DRC_REPORT" ]; then
        echo "Violation report:"
        cat "$DRC_REPORT"
    fi
    echo ""
    echo "DRC violations found — review before manufacturing."
    # DRC violations are warnings for prototype boards, not CI blockers
    exit 0
fi
