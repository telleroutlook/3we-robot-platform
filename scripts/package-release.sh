#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# Package a release: validate, build all artifacts, and create a release archive.
#
# Usage:
#   ./scripts/package-release.sh 0.2.0
#   ./scripts/package-release.sh 0.2.0 --skip-firmware

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SKIP_FIRMWARE=false

# Parse arguments
VERSION="${1:-}"
shift || true

for arg in "$@"; do
    case $arg in
        --skip-firmware) SKIP_FIRMWARE=true ;;
        --help|-h)
            echo "Usage: $0 <version> [--skip-firmware]"
            echo ""
            echo "Arguments:"
            echo "  version          Semantic version (e.g., 0.2.0)"
            echo ""
            echo "Options:"
            echo "  --skip-firmware  Skip firmware builds (useful for docs-only releases)"
            exit 0
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "ERROR: Version argument required."
    echo "Usage: $0 <version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

# Validate version format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$'; then
    echo "ERROR: Invalid version format '$VERSION'. Expected: X.Y.Z or X.Y.Z-suffix"
    exit 1
fi

RELEASE_DIR="$PROJECT_ROOT/release/v$VERSION"

echo ""
echo "============================================"
echo "  Robot Platform Release Packaging v$VERSION"
echo "============================================"
echo ""

# --- Step 1: Validation ---

echo "=== Step 1: Running validation checks ==="
echo ""

# Firmware unit tests
if [ -d "$PROJECT_ROOT/firmware/tests" ]; then
    echo "  [1/5] Firmware unit tests..."
    if (cd "$PROJECT_ROOT/firmware/tests" && make clean > /dev/null 2>&1 && make > /dev/null 2>&1 && ./test_runner > /dev/null 2>&1); then
        echo "        PASS"
    else
        echo "        FAIL — firmware unit tests did not pass"
        exit 1
    fi
else
    echo "  [1/5] Firmware tests: SKIP (directory not found)"
fi

# Python SDK tests
echo "  [2/5] Python SDK tests..."
if (cd "$PROJECT_ROOT" && python3 -m pytest sdk/tests/ --quiet --no-header 2>/dev/null); then
    echo "        PASS"
else
    echo "        FAIL — Python SDK tests did not pass"
    exit 1
fi

# TypeScript type check
echo "  [3/5] TypeScript type check..."
if (cd "$PROJECT_ROOT/sdk/web_control" && npx tsc --noEmit 2>/dev/null); then
    echo "        PASS"
else
    echo "        FAIL — TypeScript errors found"
    exit 1
fi

# Cross-layer validation
echo "  [4/5] Cross-layer type validation..."
if (cd "$PROJECT_ROOT" && npx tsx scripts/validate-ros-types.ts > /dev/null 2>&1); then
    echo "        PASS"
else
    echo "        FAIL — ROS2/TypeScript/firmware type mismatch"
    exit 1
fi

# Python lint
echo "  [5/5] Python lint..."
if (cd "$PROJECT_ROOT" && python3 -m ruff check sdk/ --quiet 2>/dev/null); then
    echo "        PASS"
else
    echo "        FAIL — Python lint errors (run: ruff check sdk/)"
    exit 1
fi

echo ""
echo "  All validation checks passed."
echo ""

# --- Step 2: Create release directory ---

echo "=== Step 2: Creating release directory ==="
mkdir -p "$RELEASE_DIR/firmware"
mkdir -p "$RELEASE_DIR/web"
mkdir -p "$RELEASE_DIR/sdk"
mkdir -p "$RELEASE_DIR/hardware"
echo "  Created: $RELEASE_DIR"
echo ""

# --- Step 3: Build firmware (all SKUs) ---

if [ "$SKIP_FIRMWARE" = false ]; then
    echo "=== Step 3: Building firmware for all SKUs ==="

    if [ -z "${IDF_PATH:-}" ]; then
        echo "  WARNING: IDF_PATH not set — skipping firmware builds"
        echo "  Run with ESP-IDF sourced, or use --skip-firmware"
    else
        SKUS="basic standard pro industrial"
        for sku in $SKUS; do
            echo "  Building SKU: $sku..."
            SKU_CONFIG="$PROJECT_ROOT/firmware/config/sdkconfig.defaults.$sku"
            if [ -f "$SKU_CONFIG" ]; then
                cp "$SKU_CONFIG" "$PROJECT_ROOT/firmware/esp32/sdkconfig.defaults"
                (cd "$PROJECT_ROOT/firmware/esp32" && \
                    idf.py set-target esp32s3 > /dev/null 2>&1 && \
                    idf.py build > /dev/null 2>&1) || {
                    echo "        FAIL — build failed for SKU: $sku"
                    exit 1
                }
                cp "$PROJECT_ROOT/firmware/esp32/build/robot-platform.bin" \
                    "$RELEASE_DIR/firmware/robot-platform-$sku.bin"
                echo "        OK → firmware/robot-platform-$sku.bin"
            else
                echo "        SKIP — config not found: $SKU_CONFIG"
            fi
        done
    fi
    echo ""
else
    echo "=== Step 3: Firmware builds SKIPPED ==="
    echo ""
fi

# --- Step 4: Build web control ---

echo "=== Step 4: Building web control UI ==="
(cd "$PROJECT_ROOT/sdk/web_control" && npm run build > /dev/null 2>&1) || {
    echo "  FAIL — web control build failed"
    exit 1
}
cp -r "$PROJECT_ROOT/sdk/web_control/dist" "$RELEASE_DIR/web/"
echo "  OK → web/dist/"
echo ""

# --- Step 5: Build Python SDK wheel ---

echo "=== Step 5: Building Python SDK package ==="
if command -v python3 -m build &> /dev/null 2>&1 || python3 -c "import build" 2>/dev/null; then
    (cd "$PROJECT_ROOT/sdk" && python3 -m build --outdir "$RELEASE_DIR/sdk/" > /dev/null 2>&1) || {
        echo "  FAIL — SDK build failed (install: pip install build)"
        exit 1
    }
    echo "  OK → sdk/*.whl, sdk/*.tar.gz"
else
    echo "  SKIP — 'build' package not installed (pip install build)"
fi
echo ""

# --- Step 6: Generate hardware files ---

echo "=== Step 6: Generating hardware manufacturing files ==="
GERBER_SCRIPT="$PROJECT_ROOT/hardware/manufacturing/generate_gerbers.sh"
if [ -x "$GERBER_SCRIPT" ] && command -v kicad-cli &> /dev/null; then
    (bash "$GERBER_SCRIPT" > /dev/null 2>&1) || echo "  WARNING: Gerber generation had issues"
    if [ -d "$PROJECT_ROOT/hardware/manufacturing/output" ]; then
        cp -r "$PROJECT_ROOT/hardware/manufacturing/output" "$RELEASE_DIR/hardware/gerbers"
        echo "  OK → hardware/gerbers/"
    fi
else
    echo "  SKIP — kicad-cli not available or script not found"
fi
echo ""

# --- Step 7: Generate changelog ---

echo "=== Step 7: Generating changelog ==="
LAST_TAG=$(git -C "$PROJECT_ROOT" describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    echo "  Changes since $LAST_TAG:"
    git -C "$PROJECT_ROOT" log "$LAST_TAG..HEAD" --oneline --no-merges > "$RELEASE_DIR/CHANGELOG.txt"
    WC=$(wc -l < "$RELEASE_DIR/CHANGELOG.txt" | tr -d ' ')
    echo "  $WC commits → CHANGELOG.txt"
else
    echo "  No previous tag found — including full log"
    git -C "$PROJECT_ROOT" log --oneline --no-merges -50 > "$RELEASE_DIR/CHANGELOG.txt"
fi
echo ""

# --- Step 8: Create manifest ---

echo "=== Step 8: Creating release manifest ==="
cat > "$RELEASE_DIR/MANIFEST.md" << EOF
# Robot Platform Release v$VERSION

**Date**: $(date -u +"%Y-%m-%d %H:%M UTC")
**Commit**: $(git -C "$PROJECT_ROOT" rev-parse --short HEAD)

## Contents

- \`firmware/\` — Compiled firmware binaries for all SKU variants
- \`web/dist/\` — Production web control UI
- \`sdk/\` — Python SDK wheel package
- \`hardware/gerbers/\` — PCB manufacturing files (Gerber + drill)
- \`CHANGELOG.txt\` — Commits since last release

## Installation

### Firmware
\`\`\`bash
./scripts/flash-firmware.sh --sku standard --port /dev/ttyUSB0
\`\`\`

### Python SDK
\`\`\`bash
pip install sdk/robot_payload_sdk-$VERSION-py3-none-any.whl
\`\`\`

### Web Control
Serve \`web/dist/\` with any static file server.
EOF
echo "  OK → MANIFEST.md"
echo ""

# --- Step 9: Create archive ---

echo "=== Step 9: Creating release archive ==="
ARCHIVE_NAME="robot-platform-v$VERSION.tar.gz"
(cd "$PROJECT_ROOT/release" && tar -czf "$ARCHIVE_NAME" "v$VERSION/")
ARCHIVE_SIZE=$(du -h "$PROJECT_ROOT/release/$ARCHIVE_NAME" | cut -f1)
echo "  OK → release/$ARCHIVE_NAME ($ARCHIVE_SIZE)"
echo ""

# --- Done ---

echo "============================================"
echo "  Release v$VERSION packaged successfully!"
echo "============================================"
echo ""
echo "  Archive: release/$ARCHIVE_NAME"
echo "  Directory: $RELEASE_DIR"
echo ""
echo "Next steps:"
echo "  1. Review CHANGELOG.txt"
echo "  2. Create git tag: git tag -a v$VERSION -m 'Release v$VERSION'"
echo "  3. Push tag: git push origin v$VERSION"
echo "  4. Create GitHub release with the archive"
