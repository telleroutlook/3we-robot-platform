#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Pre-commit validation — runs the full CLAUDE.md checklist.
# Exits 2 (BLOCK) on first failure, 0 on success.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Find Python 3.10+ (required by the SDK)
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" &>/dev/null; then
    version=$("$candidate" -c "import sys; print(sys.version_info[:2] >= (3,10))" 2>/dev/null)
    if [ "$version" = "True" ]; then
      PYTHON="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.10+ not found. Install it and retry."
  exit 2
fi

PASS=0
FAIL=0

run_step() {
  local step_num="$1"
  local desc="$2"
  shift 2

  printf "[%2d] %s ... " "$step_num" "$desc"
  if output=$("$@" 2>&1); then
    echo "PASS"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    echo "─── Output ───"
    echo "$output" | tail -30
    echo "──────────────"
    echo ""
    echo "BLOCKED: Step $step_num ($desc) failed. Fix before committing."
    exit 2
  fi
}

echo "═══════════════════════════════════════════════════════"
echo "  Pre-Commit Validation (full checklist)"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. Firmware unit tests
run_step 1 "Firmware unit tests" \
  bash -c "cd firmware/tests && make clean && make && ./build/test_runner"

# 2. TypeScript type-check
run_step 2 "TypeScript type-check (web_control)" \
  bash -c "cd sdk/web_control && npx tsc --noEmit"

# 3. Web unit tests (vitest)
run_step 3 "Web unit tests (vitest)" \
  bash -c "cd sdk/web_control && npx vitest run"

# 4. Web E2E tests (Playwright)
run_step 4 "Web E2E tests (Playwright)" \
  bash -c "cd sdk/web_control && npx playwright test"

# 5. Web lint + format
run_step 5 "Web lint (ESLint + Prettier)" \
  bash -c "cd sdk/web_control && npx eslint src/ && npx prettier --check 'src/**/*.ts'"

# 6. Python SDK tests
run_step 6 "Python SDK tests (pytest)" \
  bash -c "cd sdk/threewe && PYTHONPATH=src:\$PYTHONPATH $PYTHON -m pytest tests/ --tb=short -q"

# 7. Python lint + format
run_step 7 "Python lint (ruff)" \
  bash -c "$PYTHON -m ruff format --check sdk/ && $PYTHON -m ruff check sdk/"

# 8. Cross-layer: ROS2 ↔ TypeScript ↔ firmware
run_step 8 "Cross-layer: ROS2 ↔ TypeScript types" \
  npx tsx scripts/validate-ros-types.ts

# 9. Cross-layer: firmware params ↔ ROS2 launch
run_step 9 "Cross-layer: firmware params ↔ ROS2" \
  npx tsx scripts/validate-robot-params.ts

# 10. GPIO pin conflicts
run_step 10 "GPIO pin conflict detection" \
  "$PYTHON" scripts/validate-pin-conflicts.py

# 11. BOM ↔ firmware alignment
run_step 11 "BOM ↔ firmware alignment" \
  "$PYTHON" scripts/validate-bom-firmware.py

# 12. Kconfig constraints
run_step 12 "Kconfig constraints" \
  "$PYTHON" scripts/validate-kconfig-constraints.py

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ALL $PASS STEPS PASSED — commit allowed"
echo "═══════════════════════════════════════════════════════"
exit 0
