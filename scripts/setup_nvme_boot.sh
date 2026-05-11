#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Industrial SKU: Configure Raspberry Pi 5 for NVMe boot
#
# Prerequisites:
#   - Pi 5 with M.2 2230 NVMe SSD connected via PCIe FPC/HAT+
#   - SD card with working Raspberry Pi OS
#   - Run from the Pi 5 itself (not remote)
#
# This script:
#   1. Updates EEPROM boot order to NVMe-first
#   2. Clones SD card system to NVMe
#   3. Configures read-only rootfs overlay for reliability

set -euo pipefail

echo "=== Industrial SKU NVMe Boot Setup ==="

# Verify NVMe device exists
if [ ! -e /dev/nvme0n1 ]; then
    echo "ERROR: No NVMe device found at /dev/nvme0n1"
    echo "Verify M.2 2230 SSD is connected via PCIe FPC"
    exit 1
fi

# Verify running on Pi 5
if ! grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi 5"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo ""
echo "Step 1: Update EEPROM boot order (NVMe → SD → USB → Network)"
echo "================================================================"
sudo rpi-eeprom-config --edit <<'EOF'
BOOT_ORDER=0xf461
PCIE_PROBE=1
EOF

echo ""
echo "Step 2: Clone SD card to NVMe"
echo "================================================================"
echo "Source: /dev/mmcblk0 (SD card)"
echo "Target: /dev/nvme0n1 (NVMe SSD)"
echo ""
read -p "This will ERASE the NVMe SSD. Continue? [y/N] " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$ ]] || exit 1

sudo dd if=/dev/mmcblk0 of=/dev/nvme0n1 bs=4M status=progress conv=fsync

# Expand partition on NVMe to use full disk
echo ""
echo "Step 3: Expand root partition on NVMe"
echo "================================================================"
sudo parted /dev/nvme0n1 resizepart 2 100%
sudo e2fsck -f /dev/nvme0n1p2
sudo resize2fs /dev/nvme0n1p2

echo ""
echo "Step 4: Configure read-only rootfs overlay (optional)"
echo "================================================================"
read -p "Enable read-only overlay filesystem? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo raspi-config nonint do_overlayfs 0
    echo "Overlay FS enabled. /tmp and /var/log remain writable."
fi

echo ""
echo "=== Setup Complete ==="
echo "Remove the SD card and reboot to boot from NVMe."
echo "Verify with: lsblk | grep nvme"
