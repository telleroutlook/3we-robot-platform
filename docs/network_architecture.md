# Network Architecture

## Communication Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Devices                                 │
│  (Laptop / Phone / Tablet)                                           │
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  Web Control  │    │  Web Basic   │    │  DTLS Control Client │   │
│  │  (Lit + WS)   │    │  (HTML + WS) │    │  (Custom App)        │   │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘   │
└─────────┼────────────────────┼──────────────────────┼───────────────┘
          │ WebSocket          │ WebSocket             │ DTLS/UDP
          │ port 9090          │ port 9090             │ port 5684
          ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Companion Computer (RPi 5)                        │
│                                                                       │
│  ┌──────────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │ rosbridge_server  │    │   Nav2 Stack  │    │  micro-ROS Agent│   │
│  │ (WebSocket ↔ ROS) │    │  (Navigation) │    │  (Serial Bridge)│   │
│  └──────────────────┘    └──────────────┘    └────────┬────────┘   │
│                                                        │             │
│            ROS2 DDS (shared topic bus)                  │             │
└────────────────────────────────────────────────────────┼─────────────┘
                                                         │ UART
                                                         │ 921600 baud
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ESP32-S3 (Firmware)                              │
│                                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ micro-ROS  │  │   DTLS     │  │    UDP     │  │    Safety    │  │
│  │ (Topics +  │  │  Server    │  │  Telemetry │  │   Subsystem  │  │
│  │  Services) │  │ (Control)  │  │ (Read-only)│  │  (E-stop +   │  │
│  └────────────┘  └────────────┘  └────────────┘  │   Watchdog)  │  │
│                                                    └──────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │   Motors   │  │  Encoders  │  │ Ultrasonic │  │     IMU      │  │
│  │  (DRV8833) │  │   (PCNT)   │  │   (RMT)   │  │  (BNO055)    │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Communication Channels

### 1. micro-ROS (Primary — Sensor/Control Data)

| Property | Value |
|----------|-------|
| Transport | UART serial |
| Baudrate | 921,600 bps |
| Protocol | DDS-XRCE (micro-ROS) |
| Agent | `micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 921600` |
| Direction | Bidirectional |
| Latency | < 5ms typical |

micro-ROS exposes all sensor data and motor control to the ROS2 ecosystem. The companion computer runs the micro-ROS agent which bridges serial frames to DDS topics.

### 2. DTLS Encrypted Control (Direct Wi-Fi)

| Property | Value |
|----------|-------|
| Transport | UDP + DTLS 1.2 |
| Port | 5684 |
| Authentication | PSK (Pre-Shared Key) |
| PSK Identity | Derived from ESP32 MAC address |
| Ciphers | AES-128-GCM, AES-256-GCM (AEAD only) |
| Session cache | Yes (resume within ~60s without re-handshake) |
| Direction | Bidirectional |
| Cookie DoS protection | Yes |

Direct encrypted channel from a client app to the ESP32's Wi-Fi interface. Can send motor commands without the companion computer. Subject to the same safety limits as ROS2 commands.

### 3. UDP Telemetry (Plaintext Fallback)

| Property | Value |
|----------|-------|
| Transport | UDP |
| Port | 5685 |
| Authentication | None |
| Direction | Read-only (ESP32 → Client) |
| Use case | Debugging, real-time visualization |

Unencrypted telemetry stream. Cannot send motor commands. Useful for quick debugging without DTLS setup.

### 4. Rosbridge WebSocket (Browser ↔ ROS2)

| Property | Value |
|----------|-------|
| Transport | WebSocket (ws:// or wss://) |
| Port | 9090 |
| Protocol | rosbridge v2.0 JSON |
| Authentication | None (by default) |
| Direction | Bidirectional |
| Use case | Web UI access to all ROS2 topics/services |

The `rosbridge_server` runs on the companion computer and exposes the full ROS2 topic/service graph to browser-based clients via WebSocket.

## Port Assignment Table

| Port | Protocol | Service | Direction | Auth |
|------|----------|---------|-----------|------|
| 9090 | WebSocket | rosbridge (ROS2 ↔ browser) | Bidirectional | None |
| 5684 | UDP/DTLS | Direct motor control | Bidirectional | PSK |
| 5685 | UDP | Telemetry stream | ESP32 → Client | None |
| 8888 | UDP | micro-ROS agent (debug mode) | Bidirectional | None |
| 921600 baud | Serial | micro-ROS primary transport | Bidirectional | Physical |

## Security Model

### Who Can Send Motor Commands?

| Channel | Motor Control | Requires |
|---------|:------------:|----------|
| micro-ROS (serial) | Yes | Physical UART connection |
| DTLS (port 5684) | Yes | Valid PSK credential |
| Rosbridge (port 9090) | Yes | Network access to companion |
| UDP telemetry (5685) | **No** | — |

### Safety Enforcement (All Channels)

Regardless of which channel delivers a motor command, the firmware enforces:

1. **Speed clamping** — velocity limited to `safety_get_speed_limit()` (configurable, max 0.37 m/s)
2. **E-stop priority** — hardware E-stop cuts power via relay; software cannot override
3. **Watchdog timeout** — if no `/cmd_vel` received for 500ms, motors stop
4. **System watchdog** — if control loop stalls for 1000ms, full E-stop triggered

### PSK Provisioning

The DTLS PSK identity and key are stored in ESP32 NVS (non-volatile storage):
- Identity: `robot_<MAC_LAST_4_BYTES>`
- Key: 16-byte random, provisioned during initial setup
- Rotation: requires re-flashing NVS partition or OTA config update

## Data Flow Examples

### Joystick → Motor

```
Browser Joystick → WebSocket → rosbridge → /cmd_vel topic
  → micro-ROS agent → UART → ESP32 cmd_vel_callback()
  → safety_clamp_speed() → motor_mecanum_drive() → PWM
```

### Sensor → Dashboard

```
ESP32 ultrasonic_get_last() → range_timer_callback()
  → rcl_publish(/ultrasonic/front) → UART → micro-ROS agent
  → ROS2 DDS → rosbridge → WebSocket → <robot-sensor-radar>
```

### Emergency Stop

```
Physical button press → GPIO ISR (debounced 50ms)
  → safety_set_state(SAFETY_ESTOPPED) → motor_stop_all()
  → micro-ROS publishes /emergency_stop_state
  → Web UI <robot-estop-button> shows active E-stop
```

## Wi-Fi Configuration

The firmware connects to Wi-Fi using credentials stored in NVS. Configuration methods:

1. **Build-time** — Set `CONFIG_WIFI_SSID` / `CONFIG_WIFI_PASSWORD` in `sdkconfig`
2. **NVS provisioning** — Write credentials to the `wifi` NVS namespace before first boot
3. **Serial command** — During development, credentials can be set via serial console

The robot creates its own AP network (`RobotPlatform_XXXX`) only as a future enhancement for captive portal provisioning (not yet implemented).
