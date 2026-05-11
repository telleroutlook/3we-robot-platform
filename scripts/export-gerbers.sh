#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# Export Gerber, drill, and placement files for JLCPCB fabrication.
# Outputs to hardware/production/ directory, ready for upload.
#
# Usage:
#   ./scripts/export-gerbers.sh [--with-pos] [--with-bom]
#
# Requirements:
#   - KiCad 8+ with kicad-cli in PATH
#   - macOS: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
#     or install via: brew install --cask kicad

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PCB_FILE="$PROJECT_ROOT/hardware/pcb/robot-platform.kicad_pcb"
OUTPUT_DIR="$PROJECT_ROOT/hardware/production"

WITH_POS=false
WITH_BOM=false

for arg in "$@"; do
  case "$arg" in
    --with-pos) WITH_POS=true ;;
    --with-bom) WITH_BOM=true ;;
    --help|-h)
      echo "Usage: $0 [--with-pos] [--with-bom]"
      echo ""
      echo "Options:"
      echo "  --with-pos  Export component placement file (CPL) for SMT assembly"
      echo "  --with-bom  Remind to prepare BOM with LCSC part numbers"
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      exit 1
      ;;
  esac
done

# Locate kicad-cli
KICAD_CLI=""
if command -v kicad-cli &>/dev/null; then
  KICAD_CLI="kicad-cli"
elif [ -x "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" ]; then
  KICAD_CLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
else
  echo "ERROR: kicad-cli not found."
  echo ""
  echo "Install KiCad 8+:"
  echo "  macOS:  brew install --cask kicad"
  echo "  Linux:  sudo apt install kicad (or flatpak install org.kicad.KiCad)"
  echo ""
  echo "Or add to PATH:"
  echo "  export PATH=\"/Applications/KiCad/KiCad.app/Contents/MacOS:\$PATH\""
  exit 1
fi

echo "=== JLCPCB Gerber Export ==="
echo "KiCad CLI: $KICAD_CLI"
echo "PCB file:  $PCB_FILE"
echo "Output:    $OUTPUT_DIR"
echo ""

if [ ! -f "$PCB_FILE" ]; then
  echo "ERROR: PCB file not found: $PCB_FILE"
  exit 1
fi

# Clean and create output directory
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# --- 1. Export Gerber files ---
echo "[1/3] Exporting Gerber files..."
"$KICAD_CLI" pcb export gerbers \
  --output "$OUTPUT_DIR/" \
  --layers "F.Cu,B.Cu,In1.Cu,In2.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
  --no-protel-ext \
  --subtract-soldermask \
  "$PCB_FILE"

echo "   Gerber files exported."

# --- 2. Export drill files ---
echo "[2/3] Exporting drill files..."
"$KICAD_CLI" pcb export drill \
  --output "$OUTPUT_DIR/" \
  --format excellon \
  --excellon-units mm \
  --generate-map \
  --map-format gerberx2 \
  "$PCB_FILE"

echo "   Drill files exported."

# --- 3. Export placement/position file (optional, for SMT) ---
if [ "$WITH_POS" = true ]; then
  echo "[3/3] Exporting placement file (CPL)..."
  "$KICAD_CLI" pcb export pos \
    --output "$OUTPUT_DIR/robot-platform-pos.csv" \
    --format csv \
    --units mm \
    --side both \
    "$PCB_FILE"

  echo "   Placement file exported."
else
  echo "[3/3] Skipping placement file (use --with-pos to include)"
fi

# --- BOM reminder ---
if [ "$WITH_BOM" = true ]; then
  echo ""
  echo "=== BOM Reminder ==="
  echo "JLCPCB SMT requires a BOM CSV with columns:"
  echo "  Comment, Designator, Footprint, LCSC Part #"
  echo ""
  echo "Export from KiCad Schematic Editor:"
  echo "  Tools → Generate BOM → bom_csv_grouped_extra"
  echo ""
  echo "Then add LCSC part numbers manually or use:"
  echo "  https://yaqwsx.github.io/jlcparts/"
fi

# --- Package into ZIP ---
echo ""
echo "=== Packaging ==="
ZIP_FILE="$PROJECT_ROOT/hardware/production/robot-platform-gerbers.zip"
(cd "$OUTPUT_DIR" && zip -q "$ZIP_FILE" ./*.gbr ./*.drl ./*.gm1 2>/dev/null || \
 cd "$OUTPUT_DIR" && zip -q "$ZIP_FILE" ./* -x "*.zip")

echo "   ZIP created: $ZIP_FILE"
echo ""
echo "=== Done ==="
echo "Upload $ZIP_FILE to https://www.jlcpcb.com/quote"
echo ""

# Summary of exported files
echo "Exported files:"
ls -la "$OUTPUT_DIR/" | grep -v "^total" | grep -v "^d"
