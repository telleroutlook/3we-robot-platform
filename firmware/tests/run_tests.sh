#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Build and run firmware unit tests (host-side)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

echo "=== Building firmware unit tests ==="
cmake -B "$BUILD_DIR" -S "$SCRIPT_DIR" 2>&1
cmake --build "$BUILD_DIR" 2>&1

echo ""
echo "=== Running tests ==="
"$BUILD_DIR/test_runner"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "All tests passed!"
else
    echo ""
    echo "Some tests FAILED (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
