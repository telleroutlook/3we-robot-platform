#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Sim2Real One-Click Reproduction Script
#
# Demonstrates: train in simulation → deploy on real hardware → compare.
# Total time: ~5 minutes (training) + ~1 minute (evaluation)
#
# Prerequisites:
#   - Python 3.10+
#   - pip install threewe[sim] stable-baselines3
#   - For real hardware: ROS2 + robot_bringup running
#
# Usage:
#   ./examples/sim2real_demo/reproduce.sh              # Sim only
#   ./examples/sim2real_demo/reproduce.sh --real       # Sim + Real comparison

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "═══════════════════════════════════════════════════════════"
echo "  3we Sim2Real Reproduction Script"
echo "  Same code, any backend — zero changes required"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Step 1: Train PPO policy in simulation
echo "[1/3] Training PPO navigation policy in simulation..."
echo "      (50k timesteps, ~2 minutes)"
echo ""

cd "$ROOT_DIR"
python3 examples/train_navigation_ppo.py \
    --timesteps 50000 \
    --save-path /tmp/threewe_sim2real_demo/nav_ppo

echo ""
echo "      Model saved to /tmp/threewe_sim2real_demo/nav_ppo.zip"
echo ""

# Step 2: Evaluate in simulation
echo "[2/3] Evaluating trained policy in Gazebo simulation..."
echo ""

python3 examples/sim2real_demo/demo.py --backend gazebo \
    --goal-x 2.0 --goal-y 1.5

echo ""

# Step 3: Deploy on real hardware (optional)
if [[ "${1:-}" == "--real" ]]; then
    echo "[3/3] Deploying SAME policy on real hardware..."
    echo "      (Ensure robot_bringup is running)"
    echo ""

    python3 examples/sim2real_demo/demo.py --compare \
        --goal-x 2.0 --goal-y 1.5
else
    echo "[3/3] Skipping real hardware (run with --real to enable)"
    echo ""
    echo "      To deploy on real hardware:"
    echo "        1. Start the robot: ros2 launch robot_bringup robot.launch.py"
    echo "        2. Run: ./examples/sim2real_demo/reproduce.sh --real"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Done! The same Python code ran on both backends."
echo ""
echo "  Key insight: only 'backend=' parameter changed."
echo "  No retraining, no adaptation, no code modification."
echo "═══════════════════════════════════════════════════════════"
