# Rosbridge Integration Guide

> See also: [web_control_api.md](web_control_api.md) for the Web Components that use this connection, and [ros2_interface_reference.md](ros2_interface_reference.md) for the complete topic/service definitions.

## What is Rosbridge?

[rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite) provides a JSON-based WebSocket interface to ROS2. It allows browser-based applications (and any WebSocket client) to subscribe to topics, publish messages, and call services without a native ROS2 installation.

The robot platform uses rosbridge as the bridge between the web control UI and the ROS2 topic bus running on the companion computer.

## Architecture

```
Browser (Web Components)
    ↕ WebSocket (JSON)
rosbridge_server (on RPi5)
    ↕ ROS2 DDS
micro-ROS agent
    ↕ UART serial
ESP32-S3 firmware
```

## Installation

On the companion computer (Raspberry Pi 5):

```bash
# Install rosbridge_suite
sudo apt install ros-humble-rosbridge-suite

# Or from source (if you need the latest)
cd ~/ros2_ws/src
git clone https://github.com/RobotWebTools/rosbridge_suite.git -b ros2
cd ~/ros2_ws
colcon build --packages-select rosbridge_suite rosbridge_server rosbridge_library
```

## Launch

### Standalone

```bash
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

Default port: **9090** (WebSocket)

### With Robot Stack

The robot bringup launch file includes rosbridge:

```bash
ros2 launch robot_bringup robot.launch.py
```

### Custom Port

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=8080
```

## Protocol Overview

Rosbridge uses a JSON protocol over WebSocket. Each message has an `op` field indicating the operation.

### Subscribe to a Topic

```json
{
  "op": "subscribe",
  "topic": "/battery_state",
  "type": "sensor_msgs/msg/BatteryState"
}
```

Incoming messages arrive as:
```json
{
  "op": "publish",
  "topic": "/battery_state",
  "msg": {
    "voltage": 7.8,
    "percentage": 0.85,
    "present": true,
    "power_supply_status": 2
  }
}
```

### Publish a Message

```json
{
  "op": "publish",
  "topic": "/cmd_vel",
  "type": "geometry_msgs/msg/Twist",
  "msg": {
    "linear": { "x": 0.2, "y": 0.0, "z": 0.0 },
    "angular": { "x": 0.0, "y": 0.0, "z": 0.5 }
  }
}
```

### Call a Service

```json
{
  "op": "call_service",
  "service": "/emergency_stop",
  "type": "robot_interfaces/srv/EmergencyStop",
  "args": { "reason": "User triggered from web UI" },
  "id": "svc_1_1715000000"
}
```

Response:
```json
{
  "op": "service_response",
  "service": "/emergency_stop",
  "values": {
    "success": true,
    "current_state": 1,
    "message": "E-stop activated"
  },
  "result": true,
  "id": "svc_1_1715000000"
}
```

### Unsubscribe

```json
{
  "op": "unsubscribe",
  "topic": "/battery_state"
}
```

## Web Control Connection

The `sdk/web_control/` components use the `RosbridgeConnection` class which handles:

1. WebSocket lifecycle management
2. Auto-reconnect with exponential backoff (1s → 30s max)
3. Automatic re-subscription on reconnect
4. Zod schema validation of incoming messages
5. Service call timeout (10 seconds)

```typescript
import { connection } from './connection';

connection.connect('ws://192.168.1.100:9090');

// Subscribe
const unsub = connection.subscribe<BatteryState>(
  '/battery_state',
  'sensor_msgs/msg/BatteryState',
  (msg) => console.log(msg.voltage)
);

// Publish
connection.publish('/cmd_vel', 'geometry_msgs/msg/Twist', {
  linear: { x: 0.1, y: 0, z: 0 },
  angular: { x: 0, y: 0, z: 0 }
});

// Call service
const result = await connection.callService(
  '/emergency_stop',
  'robot_interfaces/srv/EmergencyStop',
  { reason: 'Test' }
);
```

## Web Basic Connection

The `sdk/web_basic/` minimal interface uses raw WebSocket without the connection wrapper:

```javascript
const ws = new WebSocket('ws://192.168.1.100:9090');
ws.onopen = () => {
  ws.send(JSON.stringify({
    op: 'subscribe',
    topic: '/battery_state',
    type: 'sensor_msgs/msg/BatteryState'
  }));
};
```

## Security Considerations

### Default: No Authentication

Rosbridge does **not** authenticate connections by default. Anyone with network access can:
- Read all sensor data
- Publish motor commands
- Call services (including E-stop)

### Mitigations

1. **Network isolation** — Run rosbridge only on the robot's local Wi-Fi network
2. **Firewall** — Restrict port 9090 to known client IPs
3. **wss:// with TLS** — Use a reverse proxy (nginx) for encrypted WebSocket
4. **Topic allowlist** — Configure rosbridge to expose only specific topics:

```xml
<!-- In launch file -->
<param name="topics_glob" value="['/battery_state', '/odom', '/ultrasonic/*']"/>
<param name="services_glob" value="['/emergency_stop']"/>
```

### Safety Net

Even if an unauthorized client publishes to `/cmd_vel`, the firmware enforces:
- Speed clamping (max 0.37 m/s)
- Watchdog timeout (500ms)
- E-stop override (hardware)

## Troubleshooting

### WebSocket Connection Refused

```
WebSocket connection to 'ws://192.168.1.100:9090' failed
```

1. Verify rosbridge is running: `ros2 node list | grep rosbridge`
2. Check port: `ss -tlnp | grep 9090`
3. Check firewall: `sudo ufw status`
4. Verify IP address: `hostname -I`

### No Topics Visible

The browser connects but no data arrives:

1. Check micro-ROS agent is running: `ros2 topic list`
2. Verify firmware is publishing: `ros2 topic hz /odom`
3. Check topic type matches exactly (case-sensitive)

### High Latency

Messages arrive with noticeable delay:

1. Wi-Fi congestion — move closer to AP or use 5GHz band
2. rosbridge overload — reduce subscription count or publish rate
3. micro-ROS buffer full — check serial connection quality

### Connection Drops Frequently

1. Wi-Fi signal strength: `iwconfig wlan0`
2. rosbridge memory: large message backlog can crash the server
3. Check system load: `top` on the companion computer

### Service Call Timeout

The `callService()` promise rejects after 10 seconds:

1. Verify the service exists: `ros2 service list`
2. Check service type matches: `ros2 service type /emergency_stop`
3. Ensure the firmware node is responsive (not stuck in E-stop recovery)
