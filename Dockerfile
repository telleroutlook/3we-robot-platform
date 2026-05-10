# SPDX-License-Identifier: Apache-2.0
# Multi-stage Dockerfile for the 3WE Robot Platform companion computer.
# Builds: web control UI + ROS2 workspace (bringup, diagnostics, rosbridge)
#
# Usage:
#   docker build -t robot-platform .
#   docker run -p 8080:8080 -p 9090:9090 robot-platform

# ============================================================
# Stage 1: Build web control frontend
# ============================================================
FROM node:20-alpine AS build-web

WORKDIR /app
COPY sdk/web_control/package.json sdk/web_control/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY sdk/web_control/ .
RUN npm run build

# ============================================================
# Stage 2: Build ROS2 workspace
# ============================================================
FROM ros:humble AS build-ros

WORKDIR /ros2_ws
COPY ros2_ws/robot_interfaces/ src/robot_interfaces/
COPY ros2_ws/robot_bringup/ src/robot_bringup/
COPY ros2_ws/robot_description/ src/robot_description/
COPY ros2_ws/robot_diagnostics/ src/robot_diagnostics/

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-rosbridge-server \
    ros-humble-diagnostic-msgs \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir paho-mqtt

SHELL ["/bin/bash", "-c"]
RUN source /opt/ros/humble/setup.bash && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release

# ============================================================
# Stage 3: Runtime
# ============================================================
FROM ros:humble AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    python3-pip \
    ros-humble-rosbridge-server \
    ros-humble-diagnostic-msgs \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir paho-mqtt

# Copy built ROS2 workspace
COPY --from=build-ros /ros2_ws/install /ros2_ws/install
COPY --from=build-ros /ros2_ws/src /ros2_ws/src

# Copy web frontend
COPY --from=build-web /app/dist /var/www/html

# Nginx config for SPA
RUN echo 'server { \
    listen 8080; \
    root /var/www/html; \
    location / { try_files $uri $uri/ /index.html; } \
    location /health { return 200 "ok"; add_header Content-Type text/plain; } \
}' > /etc/nginx/sites-available/default && \
    sed -i 's/^user /#user /' /etc/nginx/nginx.conf && \
    sed -i 's|/run/nginx.pid|/tmp/nginx.pid|' /etc/nginx/nginx.conf

# Entrypoint script
COPY <<'EOF' /entrypoint.sh
#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash

nginx

ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090 &
ros2 run robot_diagnostics diagnostics_node --ros-args -p robot_id:=${ROBOT_ID:-robot} &

wait -n
EOF
RUN chmod +x /entrypoint.sh

# Non-root user
RUN useradd -m -s /bin/bash robot && \
    chown -R robot:robot /ros2_ws /var/www/html && \
    chown -R robot:robot /var/log/nginx /var/lib/nginx /run

USER robot

EXPOSE 8080 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
