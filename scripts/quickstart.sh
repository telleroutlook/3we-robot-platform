#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# One-line quickstart for the 3we simulation environment.
# Usage: ./scripts/quickstart.sh

set -e

echo "=== 3we Robot Platform — Quickstart ==="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running."
    echo "Start Docker and try again."
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose (v2) is not available."
    echo "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "Building and starting simulation environment..."
echo "(This may take a few minutes on first run)"
echo ""

docker compose -f docker-compose.sim.yml up -d --build

echo ""
echo "=== Services Started ==="
echo ""
echo "  Simulation:  running (Gazebo Harmonic)"
echo "  JupyterLab:  http://localhost:8888"
echo ""
echo "To connect from Python:"
echo ""
echo "  from threewe import Robot"
echo "  async with Robot(backend='gazebo') as robot:"
echo "      image = robot.get_image()"
echo ""
echo "To stop: docker compose -f docker-compose.sim.yml down"
echo ""
