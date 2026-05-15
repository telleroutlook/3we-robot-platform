#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Script to record a terminal demo of the 3we SDK mock backend.
# Run with: asciinema rec demo/sdk_demo.cast -c "bash demo/record_demo.sh"

set -e
PYTHON=/opt/homebrew/bin/python3.12

echo ""
echo "# Install 3we SDK from source"
echo "$ pip install -e sdk/threewe/"
echo ""
$PYTHON -m pip install -e sdk/threewe/ --quiet 2>&1 | tail -1
echo ""
sleep 1

echo "# Verify installation"
echo "$ python -c \"import threewe; print(f'threewe {threewe.__version__}')\""
$PYTHON -c "import threewe; print(f'threewe {threewe.__version__}')"
echo ""
sleep 1

echo "# Run the navigation demo"
echo "$ python examples/navigate_office.py"
echo ""
sleep 0.5
$PYTHON examples/navigate_office.py
echo ""
sleep 2

echo "# Quick one-liner test"
echo "$ python -c \"..."
$PYTHON -c "
import asyncio
from threewe import Robot

async def demo():
    async with Robot(backend='mock') as robot:
        result = await robot.move_to(x=3.0, y=2.0)
        print(f'Navigation: {result.success} (distance: {result.distance:.2f}m)')
        print(f'Pose: {robot.get_pose()}')
        scan = robot.get_lidar_scan()
        print(f'LiDAR: {len(scan.ranges)} rays, min={min(scan.ranges):.2f}m')

asyncio.run(demo())
"
echo ""
sleep 2
echo "# Done! The same API works with backend=\"gazebo\" or backend=\"real\""
echo ""
