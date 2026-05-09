#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# Flash firmware to ESP32-S3 with SKU selection and port auto-detection.
#
# Usage:
#   ./scripts/flash-firmware.sh                        # auto-detect port, standard SKU
#   ./scripts/flash-firmware.sh --sku pro              # build for pro SKU
#   ./scripts/flash-firmware.sh --port /dev/ttyUSB0    # specify port
#   ./scripts/flash-firmware.sh --monitor              # attach serial monitor after flash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIRMWARE_DIR="$PROJECT_ROOT/firmware/esp32"

# Defaults
SKU="standard"
PORT=""
MONITOR=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sku)
            SKU="$2"
            shift 2
            ;;
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --monitor|-m)
            MONITOR=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --sku <variant>    SKU variant: basic, standard, pro, industrial (default: standard)"
            echo "  --port <device>    Serial port (auto-detected if not specified)"
            echo "  --monitor, -m      Attach serial monitor after flashing"
            echo ""
            echo "Examples:"
            echo "  $0                          # Auto-detect, standard SKU"
            echo "  $0 --sku pro --monitor      # Pro SKU with monitor"
            echo "  $0 --port /dev/cu.usbserial-0001 --sku industrial"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Validate SKU
VALID_SKUS="basic standard pro industrial"
if ! echo "$VALID_SKUS" | grep -qw "$SKU"; then
    echo "ERROR: Invalid SKU '$SKU'. Must be one of: $VALID_SKUS"
    exit 1
fi

# Check ESP-IDF environment
if [ -z "${IDF_PATH:-}" ]; then
    echo "ERROR: IDF_PATH not set. Source the ESP-IDF environment first:"
    echo "  . \$HOME/esp/esp-idf/export.sh"
    exit 1
fi

if ! command -v idf.py &> /dev/null; then
    echo "ERROR: idf.py not found in PATH. Ensure ESP-IDF is properly installed."
    exit 1
fi

# Auto-detect serial port
detect_port() {
    local candidates=()

    # macOS
    for p in /dev/cu.usbserial-* /dev/cu.usbmodem-* /dev/cu.SLAB_USBtoUART*; do
        [ -e "$p" ] && candidates+=("$p")
    done

    # Linux
    for p in /dev/ttyUSB* /dev/ttyACM*; do
        [ -e "$p" ] && candidates+=("$p")
    done

    if [ ${#candidates[@]} -eq 0 ]; then
        echo ""
        return
    elif [ ${#candidates[@]} -eq 1 ]; then
        echo "${candidates[0]}"
    else
        echo "Multiple serial ports found:" >&2
        for i in "${!candidates[@]}"; do
            echo "  [$i] ${candidates[$i]}" >&2
        done
        echo "${candidates[0]}"
    fi
}

if [ -z "$PORT" ]; then
    PORT=$(detect_port)
    if [ -z "$PORT" ]; then
        echo "ERROR: No serial port detected. Connect the ESP32-S3 via USB or specify --port."
        exit 1
    fi
    echo "Auto-detected port: $PORT"
fi

# Verify port exists
if [ ! -e "$PORT" ]; then
    echo "ERROR: Serial port '$PORT' does not exist."
    exit 1
fi

# Apply SKU-specific sdkconfig
SKU_CONFIG="$PROJECT_ROOT/firmware/config/sdkconfig.defaults.$SKU"
TARGET_CONFIG="$FIRMWARE_DIR/sdkconfig.defaults"

if [ ! -f "$SKU_CONFIG" ]; then
    echo "ERROR: SKU config not found: $SKU_CONFIG"
    echo "Available configs:"
    ls "$PROJECT_ROOT/firmware/config/sdkconfig.defaults."* 2>/dev/null || echo "  (none found)"
    exit 1
fi

echo ""
echo "=== Robot Platform Firmware Flash ==="
echo "  SKU:    $SKU"
echo "  Port:   $PORT"
echo "  Config: $SKU_CONFIG"
echo ""

# Copy SKU config
cp "$SKU_CONFIG" "$TARGET_CONFIG"
echo "Applied SKU config: $SKU"

# Set target and build
cd "$FIRMWARE_DIR"

echo ""
echo "--- Setting target: esp32s3 ---"
idf.py set-target esp32s3

echo ""
echo "--- Building firmware ---"
idf.py build

echo ""
echo "--- Flashing to $PORT ---"
idf.py -p "$PORT" flash

echo ""
echo "=== Flash complete ==="

# Attach monitor if requested
if [ "$MONITOR" = true ]; then
    echo ""
    echo "--- Attaching serial monitor (Ctrl+] to exit) ---"
    idf.py -p "$PORT" monitor
fi
