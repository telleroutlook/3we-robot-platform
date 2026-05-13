#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Entrypoint for simulation container — sources ROS2 and overlay.
set -e

source /opt/ros/${ROS_DISTRO}/setup.bash

if [ -f /opt/threewe/ros2_ws/install/setup.bash ]; then
    source /opt/threewe/ros2_ws/install/setup.bash
fi

exec "$@"
