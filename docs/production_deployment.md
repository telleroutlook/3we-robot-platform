# Production Deployment Guide

This guide covers deploying the 3WE Robot Platform to production robots.

## Pre-Deployment Checklist

### Firmware

- [ ] Production sdkconfig applied (`sdkconfig.defaults.production`)
- [ ] Secure boot signing key generated and stored securely
- [ ] NVS encryption key provisioned per device
- [ ] DTLS PSK provisioned per device (see `docs/secrets_management.md`)
- [ ] OTA public key provisioned per device
- [ ] Firmware binary signed with OTA private key
- [ ] Flash encryption enabled (one-time eFuse burn — irreversible)

### Companion Computer

- [ ] Docker image built and tagged with release version
- [ ] MQTT credentials configured for fleet telemetry
- [ ] Wi-Fi/Ethernet network configured for robot operation environment
- [ ] ROS_DOMAIN_ID set to avoid DDS conflicts with other robots on network

### Network

- [ ] DTLS control channel tested end-to-end
- [ ] Rosbridge accessible only from companion (not exposed to external network)
- [ ] Web UI accessible only on local network (or behind VPN)
- [ ] MQTT broker uses TLS in production

## Firmware Deployment

### First-Time Flash (Factory)

```bash
# 1. Provision keys to device NVS
provision-keys generate --output keys/DEVICE_MAC.json
provision-keys flash --keys keys/DEVICE_MAC.json --port /dev/ttyUSB0

# 2. Flash production firmware
cd firmware/esp32
idf.py -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.standard;sdkconfig.defaults.production" \
  set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash

# 3. Verify device boots and DTLS channel establishes
idf.py -p /dev/ttyUSB0 monitor
```

### Over-the-Air Updates

See `docs/fleet_ota_strategy.md` for the full OTA rollout process.

```bash
# Sign the firmware binary
espsecure.py sign_data \
  --version 2 \
  --keyfile keys/ota_signing_key.pem \
  --output build/robot-platform-signed.bin \
  build/robot-platform.bin

# Host the signed binary on an HTTPS server
# Trigger OTA via DTLS command channel or ROS2 service
```

## Companion Computer Setup

### Using Docker (Recommended)

```bash
# Pull release image (or build locally)
docker pull ghcr.io/3we/robot-platform:v0.2.0

# Run with environment configuration
docker run -d \
  --name robot-companion \
  --restart unless-stopped \
  -p 8080:8080 \
  -p 9090:9090 \
  -e ROBOT_ID=robot-001 \
  -e ROS_DOMAIN_ID=42 \
  ghcr.io/3we/robot-platform:v0.2.0
```

### Using Docker Compose

```bash
# Copy .env.example to .env, configure
cp .env.example .env
vim .env

# Start core stack
docker compose up -d

# Start with fleet telemetry
docker compose --profile fleet up -d
```

### Direct Installation (Without Docker)

For Jetson Nano, Raspberry Pi, or other SBCs where Docker overhead is undesirable:

```bash
# 1. Install ROS2 Humble
# Follow https://docs.ros.org/en/humble/Installation.html

# 2. Build workspace
cd ros2_ws
colcon build --symlink-install

# 3. Install Python dependencies
pip install paho-mqtt

# 4. Build web control
cd sdk/web_control && npm ci && npm run build

# 5. Serve with nginx (copy dist/ to /var/www/html)

# 6. Launch
source install/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ros2 run robot_diagnostics diagnostics_node --ros-args -p robot_id:=robot-001 &
```

## Monitoring Setup

### Fleet Telemetry

Enable MQTT bridge for centralized monitoring:

```bash
ros2 run robot_diagnostics mqtt_bridge_node --ros-args \
  -p broker_url:=mqtts://fleet-broker.example.com:8883 \
  -p username:=robot-001 \
  -p password:=$MQTT_PASSWORD \
  -p robot_id:=robot-001
```

See `docs/fleet_telemetry.md` for Grafana/InfluxDB setup.

### Health Monitoring

The web UI at `http://<companion>:8080` includes a system health panel showing:
- Connection status (WebSocket heartbeat)
- Battery level and alerts
- E-stop state
- Topic publication rates
- Uptime

External monitoring can poll `http://<companion>:8080/health` for a simple OK/fail response.

## Rollback Procedure

### Firmware Rollback

ESP-IDF's A/B partition scheme supports automatic rollback:

1. If new firmware fails boot validation (safety self-test), bootloader reverts to previous partition
2. Manual rollback: `idf.py -p /dev/ttyUSB0 erase-otadata` (reverts to factory image)
3. Full recovery: Flash factory image via UART (requires physical access)

### Companion Rollback

```bash
# Docker: revert to previous image tag
docker stop robot-companion
docker run -d --name robot-companion ghcr.io/3we/robot-platform:v0.1.0

# Or use Docker Compose with pinned image version in override
```

## Network Security

### Recommended Topology

```
[Internet] ─── [Firewall/Router] ─── [Robot LAN]
                                          │
                          ┌───────────────┼───────────────┐
                          │               │               │
                    [Companion]    [ESP32 Firmware]   [Operator PC]
                    :8080 web      :5684 DTLS ctrl    Web browser
                    :9090 rosbridge
```

- ESP32 DTLS channel (port 5684) only accepts authenticated PSK connections
- Rosbridge (port 9090) should only be accessible from the companion container
- Web UI (port 8080) accessible on robot LAN for operators
- No ports exposed to the internet unless behind VPN

### Firewall Rules

```bash
# Only allow DTLS from companion to ESP32
iptables -A FORWARD -p udp --dport 5684 -s <companion_ip> -j ACCEPT
iptables -A FORWARD -p udp --dport 5684 -j DROP
```
