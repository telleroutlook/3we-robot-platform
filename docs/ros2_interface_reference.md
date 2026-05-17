# ROS2 Interface Reference

Complete reference for all ROS2 topics, services, and coordinate frames published by the robot platform.

## Node

| Property | Value |
|----------|-------|
| Node name | `robot_base` |
| Namespace | `/` (root) |
| Transport | micro-ROS via UART (921600 baud) |
| Agent | `micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 921600` |

## Published Topics

### /odom

| Property | Value |
|----------|-------|
| Type | `nav_msgs/msg/Odometry` |
| Rate | 50 Hz |
| QoS | Best Effort, Volatile, Keep Last 5 |
| Frame | `odom` → `base_link` |

Wheel odometry fused with IMU yaw (when BNO055 is available). Position is integrated from mecanum forward kinematics.

Fields populated:
- `pose.pose.position.{x, y}` — accumulated position (m)
- `pose.pose.orientation.{z, w}` — yaw as quaternion
- `twist.twist.linear.{x, y}` — current velocity (m/s)
- `twist.twist.angular.z` — current yaw rate (rad/s)

### /wheel_speeds

| Property | Value |
|----------|-------|
| Type | `std_msgs/msg/Float32MultiArray` |
| Rate | 50 Hz |
| QoS | Best Effort, Volatile, Keep Last 5 |

Individual wheel linear velocities in m/s. Array order: `[FL, FR, RL, RR]`.

The custom `robot_interfaces/msg/WheelSpeeds` message provides named fields for the same data via the rosbridge interface.

### /battery_state

| Property | Value |
|----------|-------|
| Type | `sensor_msgs/msg/BatteryState` |
| Rate | 1 Hz |
| QoS | Reliable, Transient Local, Keep Last 1 |

Battery monitoring for 2S LiPo (7.4V nominal).

Fields populated:
- `voltage` — pack voltage (V), range 6.0–8.4V
- `percentage` — state of charge (0.0–1.0)
- `present` — always `true`
- `power_supply_status` — 2 (DISCHARGING) or 4 (NOT_CHARGING at critical)

### /ultrasonic/front, /ultrasonic/back, /ultrasonic/left, /ultrasonic/right

| Property | Value |
|----------|-------|
| Type | `sensor_msgs/msg/Range` |
| Rate | 10 Hz (each) |
| QoS | Best Effort, Volatile, Keep Last 1 |
| Frame | `ultrasonic_front`, `ultrasonic_back`, `ultrasonic_left`, `ultrasonic_right` |

HC-SR04 ultrasonic distance sensors.

Fields populated:
- `radiation_type` — `ULTRASOUND` (0)
- `field_of_view` — 0.26 rad (~15°)
- `min_range` — 0.02 m
- `max_range` — 4.0 m
- `range` — measured distance (m); returns `max_range` when no obstacle

### /emergency_stop_state

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/msg/EmergencyStopState` |
| Rate | On change (+ periodic at 1 Hz) |
| QoS | Reliable, Transient Local, Keep Last 10 |

```
std_msgs/Header header
bool stopped                    # Whether E-stop is currently active
uint8 state                     # 0=normal, 1=estopped, 2=recovery_pending
string reason                   # Human-readable reason for last E-stop

uint8 STATE_NORMAL=0
uint8 STATE_ESTOPPED=1
uint8 STATE_RECOVERY=2
```

### /payload/state

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/msg/PayloadState` |
| Rate | On change |
| QoS | Reliable, Transient Local, Keep Last 1 |

```
std_msgs/Header header
string payload_id               # EEPROM-read identifier
string name                     # Human-readable name from EEPROM
bool connected                  # Physical connection detected
bool power_5v_active            # 5V rail enabled
bool power_12v_active           # 12V rail enabled
bool power_vbat_active          # VBAT rail enabled
float32 current_5v              # Current draw on 5V rail (A)
float32 current_12v             # Current draw on 12V rail (A)
float32 power_consumption_watts # Total power consumption (W)
uint8 status                    # 0=idle, 1=active, 2=error, 3=updating

uint8 STATUS_IDLE=0
uint8 STATUS_ACTIVE=1
uint8 STATUS_ERROR=2
uint8 STATUS_UPDATING=3
```

## Subscribed Topics

### /cmd_vel

| Property | Value |
|----------|-------|
| Type | `geometry_msgs/msg/Twist` |
| Expected rate | 10–50 Hz |
| QoS | Reliable, Volatile, Keep Last 1 |
| Timeout | 500ms (motors stop if no message received) |

Velocity command for mecanum drive:
- `linear.x` — forward/backward (m/s), clamped to ±0.37
- `linear.y` — strafe left/right (m/s), clamped to ±0.37
- `angular.z` — rotation (rad/s), clamped to ±3.0

Commands are safety-clamped by `safety_clamp_speed()` and ignored entirely when E-stop is active.

## Services

### /emergency_stop

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/srv/EmergencyStop` |
| Behavior | One-way activation only |

```
# Request
string reason               # Human-readable reason for E-stop

# Response
bool success
uint8 current_state         # 0=normal, 1=estopped, 2=recovery_pending, 3=relay_fault
string message
```

Software E-stop activation. Cannot reset via software — physical button release + hardware acknowledgment required.

### /payload_power

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/srv/PayloadPower` |
| Behavior | Toggle individual power rails |

```
# Request
string payload_id
string rail                 # "5V", "12V", or "VBAT"
bool enable

# Response
bool success
string message
```

### /undock_robot

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/srv/UndockRobot` |
| Behavior | Reverse out of charging dock |

```
# Request
float32 reverse_distance    # Meters to reverse after undocking (default 0.3)

# Response
bool success
string error_message
```

### /arm_command

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/srv/ArmCommand` |
| Behavior | Command the robotic arm + vacuum pump payload |

```
# Request
string command              # "pick", "place", "home", etc.
float64 target_x
float64 target_y
float64 target_z

# Response
bool success
string message
```

### /basket_dump

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/srv/BasketDump` |
| Behavior | Command the tipping basket servo |

```
# Request
bool dump                   # true = tip to dump, false = return to upright

# Response
bool success
string message
```

## Actions

### /dock

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/action/Dock` |
| Behavior | Navigate to and dock at a charging station |

```
# Goal
string dock_id              # Identifier for target dock (empty = nearest)

# Result
bool success
string error_message
float32 total_duration_sec

# Feedback
uint8 stage                 # Same enum as DockingState.msg
float32 progress            # 0.0-1.0
float64 distance_to_dock
```

Stages: IDLE(0) → APPROACH(1) → VISUAL_SERVO_COARSE(2) → VISUAL_SERVO_FINE(3) → CONTACT_VERIFY(4) → DOCKED(5). UNDOCKING(6) and FAILED(7) are terminal/error states.

### /collect_balls

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/action/CollectBalls` |
| Behavior | Autonomous ball collection cycle (search → pick → return → dump) |

```
# Goal
string zone_id              # Target zone for collection (empty = all)
uint8 max_balls 0           # Stop after N balls (0 = unlimited)

# Result
bool success
string error_message
uint8 total_collected
float32 total_duration_sec

# Feedback
uint8 state                 # CollectionState enum (0-5)
uint8 balls_in_basket
uint8 total_collected
string current_phase
```

Stages: IDLE(0) → SEARCHING(1) → APPROACHING(2) → PICKING(3) → RETURNING(4) → DUMPING(5).

## Additional Published Topics

### /docking_state

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/msg/DockingState` |
| Rate | On change |
| QoS | Reliable, Transient Local, Keep Last 1 |

```
uint8 IDLE=0
uint8 APPROACH=1
uint8 VISUAL_SERVO_COARSE=2
uint8 VISUAL_SERVO_FINE=3
uint8 CONTACT_VERIFY=4
uint8 DOCKED=5
uint8 UNDOCKING=6
uint8 FAILED=7

uint8 stage
float32 progress            # 0.0-1.0 overall progress estimate
string error_message        # Non-empty when stage==FAILED
float64 distance_to_dock    # Meters (from visual estimate), -1 if unknown
```

### /collection/state

| Property | Value |
|----------|-------|
| Type | `robot_interfaces/msg/CollectionState` |
| Rate | On change |
| QoS | Reliable, Transient Local, Keep Last 1 |

```
uint8 IDLE=0
uint8 SEARCHING=1
uint8 APPROACHING=2
uint8 PICKING=3
uint8 RETURNING=4
uint8 DUMPING=5

uint8 state
uint8 balls_in_basket
uint8 total_collected
string error_message
```

Published by `collection_manager` node. State machine feedback for autonomous ball collection.

### /diagnostics

| Property | Value |
|----------|-------|
| Type | `diagnostic_msgs/msg/DiagnosticArray` |
| Rate | 10 Hz (configurable) |
| QoS | Reliable, Volatile, Keep Last 10 |

Published by `robot_diagnostics` node. Aggregates system, battery, safety, and topic health into standard ROS2 diagnostics format. Status names follow the pattern `{robot_id}/{category}` (e.g., `robot-01/safety`, `robot-01/battery`).

## Coordinate Frames

```
odom
 └── base_link
      ├── ultrasonic_front
      ├── ultrasonic_back
      ├── ultrasonic_left
      ├── ultrasonic_right
      ├── imu_link
      └── payload_mount
```

| Frame | Description |
|-------|-------------|
| `odom` | Fixed world frame (drift accumulates) |
| `base_link` | Robot center, ground plane |
| `ultrasonic_*` | Sensor mounting positions |
| `imu_link` | BNO055 IMU location |
| `payload_mount` | PBC-34 connector center |

## QoS Profile Summary

| Topic | Reliability | Durability | History | Deadline |
|-------|------------|------------|---------|----------|
| /cmd_vel | Reliable | Volatile | Keep Last 1 | 100ms |
| /odom | Best Effort | Volatile | Keep Last 5 | 25ms |
| /ultrasonic/* | Best Effort | Volatile | Keep Last 1 | 120ms |
| /battery_state | Reliable | Transient Local | Keep Last 1 | 2000ms |
| /emergency_stop | Reliable | Transient Local | Keep Last 10 | 50ms |
| /payload/state | Reliable | Transient Local | Keep Last 1 | — |
| /wheel_speeds | Best Effort | Volatile | Keep Last 5 | 25ms |

Full QoS configuration: [`ros2_ws/robot_bringup/config/qos_profiles.yaml`](https://github.com/telleroutlook/3we-robot-platform/blob/main/ros2_ws/robot_bringup/config/qos_profiles.yaml)

## Data Rate Budget

| Topic | Rate | Approx. Bandwidth |
|-------|------|-------------------|
| /odom | 50 Hz | ~5 KB/s |
| /wheel_speeds | 50 Hz | ~2 KB/s |
| /ultrasonic/* (×4) | 10 Hz | ~2 KB/s |
| /battery_state | 1 Hz | ~0.1 KB/s |
| /cmd_vel (in) | 10–50 Hz | ~1–5 KB/s |
| **Total** | — | **~10–15 KB/s** |

The micro-ROS serial link at 921600 baud supports ~90 KB/s theoretical throughput, providing ample headroom.
