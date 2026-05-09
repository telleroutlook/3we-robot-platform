#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# Development environment setup script for the Robot Platform.
# Detects OS, checks prerequisites, installs dependencies, and validates the setup.
#
# Usage: ./scripts/setup-dev-env.sh [--skip-firmware] [--skip-ros2]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SKIP_FIRMWARE=false
SKIP_ROS2=false

for arg in "$@"; do
    case $arg in
        --skip-firmware) SKIP_FIRMWARE=true ;;
        --skip-ros2) SKIP_ROS2=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-firmware] [--skip-ros2]"
            echo ""
            echo "Options:"
            echo "  --skip-firmware  Skip ESP-IDF / firmware toolchain check"
            echo "  --skip-ros2      Skip ROS2 installation check"
            exit 0
            ;;
    esac
done

# --- Helpers ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

ERRORS=()

check_command() {
    local cmd=$1
    local name=${2:-$1}
    local install_hint=${3:-""}
    if command -v "$cmd" &> /dev/null; then
        ok "$name found: $(command -v "$cmd")"
        return 0
    else
        fail "$name not found"
        if [ -n "$install_hint" ]; then
            echo "       Install: $install_hint"
        fi
        ERRORS+=("$name not found")
        return 1
    fi
}

check_version() {
    local cmd=$1
    local min_version=$2
    local actual_version=$3
    local name=${4:-$cmd}

    if [ "$(printf '%s\n' "$min_version" "$actual_version" | sort -V | head -n1)" = "$min_version" ]; then
        ok "$name version $actual_version (>= $min_version)"
        return 0
    else
        fail "$name version $actual_version (need >= $min_version)"
        ERRORS+=("$name version too old: $actual_version < $min_version")
        return 1
    fi
}

detect_os() {
    case "$(uname -s)" in
        Linux*)
            if grep -q Microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        Darwin*) echo "macos" ;;
        *) echo "unknown" ;;
    esac
}

# --- Main ---

echo ""
echo "========================================"
echo "  Robot Platform — Dev Environment Setup"
echo "========================================"
echo ""

OS=$(detect_os)
info "Detected OS: $OS"
echo ""

# --- 1. Python ---

info "Checking Python..."
if check_command python3 "Python 3"; then
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    check_version python3 "3.10" "$PY_VERSION" "Python"
fi
echo ""

# --- 2. Node.js ---

info "Checking Node.js..."
if check_command node "Node.js" "https://nodejs.org/ or use nvm"; then
    NODE_VERSION=$(node -v | sed 's/^v//')
    check_version node "18.0.0" "$NODE_VERSION" "Node.js"
fi
check_command npm "npm"
echo ""

# --- 3. ESP-IDF (firmware) ---

if [ "$SKIP_FIRMWARE" = false ]; then
    info "Checking ESP-IDF..."
    if [ -n "${IDF_PATH:-}" ]; then
        ok "IDF_PATH is set: $IDF_PATH"
        if check_command idf.py "idf.py"; then
            IDF_VERSION=$(idf.py --version 2>/dev/null || echo "unknown")
            info "ESP-IDF version: $IDF_VERSION"
        fi
    else
        warn "IDF_PATH not set — firmware builds will not work"
        echo "       Install ESP-IDF: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/get-started/"
        echo "       Then run: . \$HOME/esp/esp-idf/export.sh"
        ERRORS+=("IDF_PATH not set")
    fi
    echo ""
fi

# --- 4. ROS2 (optional) ---

if [ "$SKIP_ROS2" = false ]; then
    info "Checking ROS2..."
    if [ -n "${ROS_DISTRO:-}" ]; then
        ok "ROS_DISTRO is set: $ROS_DISTRO"
        check_command colcon "colcon" "sudo apt install python3-colcon-common-extensions"
    else
        warn "ROS2 not sourced — ROS2 builds will not work"
        echo "       Install: https://docs.ros.org/en/humble/Installation.html"
        echo "       Then run: source /opt/ros/humble/setup.bash"
    fi
    echo ""
fi

# --- 5. Install Python SDK ---

info "Installing Python SDK in editable mode..."
if [ -f "$PROJECT_ROOT/sdk/pyproject.toml" ]; then
    pip install -e "$PROJECT_ROOT/sdk/[dev]" --quiet 2>/dev/null && \
        ok "Python SDK installed (editable)" || \
        { fail "Python SDK install failed"; ERRORS+=("SDK install failed"); }
else
    fail "sdk/pyproject.toml not found"
    ERRORS+=("sdk/pyproject.toml missing")
fi
echo ""

# --- 6. Install web_control dependencies ---

info "Installing web_control dependencies..."
if [ -f "$PROJECT_ROOT/sdk/web_control/package.json" ]; then
    (cd "$PROJECT_ROOT/sdk/web_control" && npm ci --silent 2>/dev/null) && \
        ok "web_control dependencies installed" || \
        { fail "npm ci failed in sdk/web_control"; ERRORS+=("web_control npm ci failed"); }
else
    fail "sdk/web_control/package.json not found"
    ERRORS+=("web_control/package.json missing")
fi
echo ""

# --- 7. Install Playwright browsers ---

info "Installing Playwright browsers..."
if (cd "$PROJECT_ROOT/sdk/web_control" && npx playwright install chromium --with-deps 2>/dev/null); then
    ok "Playwright Chromium installed"
else
    warn "Playwright browser install failed (E2E tests may not run)"
fi
echo ""

# --- 8. Install root dependencies (validate-ros-types) ---

info "Installing root dependencies..."
if [ -f "$PROJECT_ROOT/package.json" ]; then
    (cd "$PROJECT_ROOT" && npm ci --silent 2>/dev/null) && \
        ok "Root dependencies installed" || \
        warn "Root npm ci failed (validate-ros-types may not run)"
fi
echo ""

# --- 9. Validation ---

echo ""
echo "========================================"
echo "  Running validation checks"
echo "========================================"
echo ""

# Firmware host tests
if [ "$SKIP_FIRMWARE" = false ] && [ -d "$PROJECT_ROOT/firmware/tests" ]; then
    info "Building firmware unit tests (host)..."
    if (cd "$PROJECT_ROOT/firmware/tests" && make clean > /dev/null 2>&1 && make > /dev/null 2>&1); then
        ok "Firmware unit tests build"
    else
        warn "Firmware unit test build failed (GCC required)"
    fi
fi

# Python tests
info "Running Python SDK tests..."
if (cd "$PROJECT_ROOT" && python3 -m pytest sdk/tests/ --quiet --no-header 2>/dev/null); then
    ok "Python SDK tests pass"
else
    warn "Python SDK tests failed"
fi

# TypeScript type check
info "Checking web_control TypeScript..."
if (cd "$PROJECT_ROOT/sdk/web_control" && npx tsc --noEmit 2>/dev/null); then
    ok "web_control TypeScript check passes"
else
    warn "web_control TypeScript check failed"
fi

# Python lint
info "Running ruff check..."
if (cd "$PROJECT_ROOT" && python3 -m ruff check sdk/ --quiet 2>/dev/null); then
    ok "Python lint passes"
else
    warn "Python lint found issues (run: ruff check sdk/)"
fi

# --- Summary ---

echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo ""

if [ ${#ERRORS[@]} -eq 0 ]; then
    echo -e "${GREEN}All prerequisites satisfied!${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Firmware build:  cd firmware/esp32 && idf.py build"
    echo "  - ROS2 build:      cd ros2_ws && colcon build --symlink-install"
    echo "  - Web dev server:  cd sdk/web_control && npm run dev"
    echo "  - Run all tests:   pytest sdk/tests/ && cd sdk/web_control && npx playwright test"
    echo ""
else
    echo -e "${YELLOW}Setup completed with ${#ERRORS[@]} issue(s):${NC}"
    for err in "${ERRORS[@]}"; do
        echo -e "  ${RED}•${NC} $err"
    done
    echo ""
    echo "Fix the issues above, then re-run: ./scripts/setup-dev-env.sh"
fi
