# Web Control API Reference

The web control interface provides 8 custom Web Components for robot teleoperation and monitoring. Components connect to the robot via the [rosbridge WebSocket protocol](rosbridge_guide.md).

## Setup

### Installation

```bash
cd sdk/web_control
npm ci
npm run build    # production build → dist/
npm run dev      # development server with hot reload
```

### Usage in HTML

```html
<script type="module" src="dist/main.js"></script>

<robot-joystick></robot-joystick>
<robot-battery-gauge></robot-battery-gauge>
<robot-sensor-radar></robot-sensor-radar>
<robot-estop-button></robot-estop-button>
<robot-payload-panel></robot-payload-panel>
<robot-wheel-speeds></robot-wheel-speeds>
<robot-imu-attitude></robot-imu-attitude>
<robot-system-status></robot-system-status>
```

### Connection

All components share a singleton `RosbridgeConnection` instance:

```typescript
import { connection } from './connection';

// Connect to rosbridge
connection.connect('ws://192.168.1.100:9090');

// Monitor connection state
connection.addEventListener('statechange', (e: CustomEvent) => {
  console.log(e.detail.state); // 'disconnected' | 'connecting' | 'connected' | 'error'
});

// Disconnect
connection.disconnect();
```

The connection auto-reconnects with exponential backoff (1s → 2s → 4s → ... → 30s max).

---

## Components

### `<robot-joystick>`

Touch/pointer-based joystick for mecanum drive teleoperation.

| Property | Description |
|----------|-------------|
| ROS topic (publish) | `/cmd_vel` (`geometry_msgs/msg/Twist`) |
| Publish rate | ~20 Hz while active |
| Velocity range | ±1.0 m/s linear (default limit), ±3.0 rad/s angular |

**Behavior:**
- Drag the knob to publish velocity commands
- Supports touch, mouse, and pointer events
- Returns to center (zero velocity) on release
- Horizontal axis → `linear.y` (strafe)
- Vertical axis → `linear.x` (forward/back)

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--joystick-size` | `200px` | Outer ring diameter |
| `--joystick-knob-size` | `60px` | Inner knob diameter |
| `--color-accent` | `#3b82f6` | Active knob color |

---

### `<robot-battery-gauge>`

Battery voltage and state-of-charge display.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/battery_state` (`sensor_msgs/msg/BatteryState`) |

**Display:**
- Voltage in volts (e.g., "7.8V")
- Percentage as filled bar (0–100%)
- Color changes: green (>60%), yellow (20–60%), red (<20%)
- "CRITICAL" warning when below 3.0V/cell

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--color-success` | `#22c55e` | Good battery color |
| `--color-warning` | `#eab308` | Low battery color |
| `--color-danger` | `#ef4444` | Critical battery color |

---

### `<robot-sensor-radar>`

360-degree proximity visualization from ultrasonic sensors.

| Property | Description |
|----------|-------------|
| ROS topics (subscribe) | `/ultrasonic/front`, `/ultrasonic/back`, `/ultrasonic/left`, `/ultrasonic/right` (all `sensor_msgs/msg/Range`) |

**Display:**
- Top-down radar view with robot silhouette at center
- Distance arcs for each sensor direction
- Color-coded proximity: green (safe) → yellow (close) → red (danger)
- Numeric distance labels in meters

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--radar-size` | `200px` | Radar display diameter |
| `--color-safe` | `#22c55e` | Far distance color |
| `--color-close` | `#eab308` | Medium distance color |
| `--color-danger` | `#ef4444` | Near distance color |

---

### `<robot-estop-button>`

Emergency stop trigger and state display.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/emergency_stop_state` (`robot_interfaces/msg/EmergencyStopState`) |
| ROS service (call) | `/emergency_stop` (`robot_interfaces/srv/EmergencyStop`) |

**Behavior:**
- Large button — click to trigger software E-stop
- Displays current state: NORMAL (green), ESTOPPED (red pulsing), RECOVERY (yellow)
- Shows reason text from last E-stop event
- Confirmation dialog before triggering
- Cannot reset via UI (requires physical hardware action)

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--estop-size` | `80px` | Button diameter |
| `--color-estop-active` | `#dc2626` | Active E-stop color |
| `--color-estop-normal` | `#16a34a` | Normal state color |

---

### `<robot-payload-panel>`

Payload connection status and power rail management.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/payload/state` (`robot_interfaces/msg/PayloadState`) |
| ROS service (call) | `/payload_power` (`robot_interfaces/srv/PayloadPower`) |

**Display:**
- Payload name and ID (from EEPROM)
- Connection indicator (connected/disconnected)
- Power rail toggles: 5V, 12V, VBAT
- Current draw per rail (A)
- Total power consumption (W)
- Status badge: idle, active, error, updating

**Behavior:**
- Toggle buttons call `/payload_power` service to enable/disable rails
- Disabled when no payload connected
- Shows error state with message on service call failure

---

### `<robot-wheel-speeds>`

Real-time wheel speed indicator for all 4 motors.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/wheel_speeds` (`std_msgs/msg/Float32MultiArray`) |

**Display:**
- 4 horizontal bars (FL, FR, RL, RR)
- Bar length proportional to wheel speed
- Green for forward, red for reverse
- Numeric speed in m/s

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--bar-height` | `20px` | Speed bar height |
| `--color-forward` | `#22c55e` | Forward motion color |
| `--color-reverse` | `#ef4444` | Reverse motion color |

---

### `<robot-imu-attitude>`

3D attitude visualization from IMU data.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/imu/data` (`sensor_msgs/msg/Imu`) |

**Display:**
- Animated 3D box representing robot orientation
- Roll, pitch, yaw angles in degrees
- Uses CSS 3D transforms for visualization
- Falls back gracefully when IMU is unavailable

---

### `<robot-system-status>`

Aggregated system health overview from ROS2 diagnostics.

| Property | Description |
|----------|-------------|
| ROS topic (subscribe) | `/diagnostics` (`diagnostic_msgs/msg/DiagnosticArray`) |

**Display:**
- Grid of subsystem status indicators (motors, IMU, battery, comms, etc.)
- Color-coded severity: green (OK), amber (WARN), red (ERROR), gray (STALE)
- Shows subsystem name and diagnostic message
- Dims automatically if no update received within 5 seconds (stale detection)

**CSS Custom Properties:**

| Property | Default | Description |
|----------|---------|-------------|
| `--color-surface-raised` | `#f5f5f5` | Item background color |

---

## Events

All components dispatch standard DOM events for external integration:

| Event | Dispatched by | Detail |
|-------|--------------|--------|
| `estop-triggered` | `<robot-estop-button>` | `{ reason: string }` |
| `joystick-move` | `<robot-joystick>` | `{ vx: number, vy: number }` |
| `rail-toggled` | `<robot-payload-panel>` | `{ rail: string, enabled: boolean }` |

## Embedding in External Pages

Components are standard Web Components and work in any HTML page:

```html
<!DOCTYPE html>
<html>
<head>
  <script type="module">
    import './dist/main.js';
    import { connection } from './dist/connection.js';
    connection.connect('ws://robot.local:9090');
  </script>
</head>
<body>
  <robot-joystick></robot-joystick>
  <robot-battery-gauge></robot-battery-gauge>
</body>
</html>
```

No framework dependency required — works with React, Vue, Svelte, or vanilla HTML.

## Type Definitions

TypeScript interfaces for all ROS message types are exported from `src/types.ts`:

```typescript
import type {
  Twist,
  BatteryState,
  Range,
  Imu,
  WheelSpeeds,
  PayloadState,
  EmergencyStopState,
} from './types';
```

See [`sdk/web_control/src/types.ts`](../sdk/web_control/src/types.ts) for the full type definitions.
