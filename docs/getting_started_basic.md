# Getting Started — Basic SKU

> SPDX-License-Identifier: Apache-2.0

The Basic SKU (¥999) is a standalone ESP32-S3 mobile platform for learning embedded programming, robotics fundamentals, and FreeRTOS concepts. No companion computer (Pi 5) or ROS2 knowledge is required.

## What's in the Box

- 4WD Mecanum chassis (300 × 250 mm)
- ESP32-S3-WROOM-1 control board (8MB Flash, 8MB PSRAM)
- 4× N20 gear motors (1:90) with magnetic encoders
- 4× HC-SR04 ultrasonic sensors
- BNO055 IMU module
- 2S 6000mAh LiPo battery
- USB-C programming cable

## Development Environment

### Option A: ESP-IDF (Recommended)

```bash
# Install ESP-IDF 5.x (Linux/macOS)
mkdir -p ~/esp && cd ~/esp
git clone -b v5.2 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32s3
source export.sh

# Build and flash the Basic firmware
cd path/to/3we-robot-platform/firmware/esp32
idf.py set-target esp32s3
idf.py build flash monitor
```

### Option B: Arduino IDE

The ESP32-S3 is compatible with the Arduino ESP32 core. Install via Board Manager:
- Board: ESP32-S3 Dev Module
- Flash: 8MB, PSRAM: Enabled

## WiFi Remote Control

The Basic SKU uses WiFi UDP direct control (no ROS2). Connect from any device on the same network:

### Python Controller Example

```python
import socket
import struct
import time

ROBOT_IP = "192.168.4.1"  # AP mode default
CMD_PORT = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_velocity(vx, vy, omega):
    """Send cmd_vel: vx (m/s), vy (m/s), omega (rad/s)"""
    packet = struct.pack('<3f', vx, vy, omega)
    sock.sendto(packet, (ROBOT_IP, CMD_PORT))

# Drive forward at 0.2 m/s for 3 seconds
for _ in range(30):
    send_velocity(0.2, 0.0, 0.0)
    time.sleep(0.1)

# Stop
send_velocity(0.0, 0.0, 0.0)
```

## Learning Exercises

### 1. PID Tuning

The firmware runs a PID velocity controller at 50Hz. Adjust gains via `menuconfig`:

```bash
idf.py menuconfig
# Navigate: Robot Platform → Motor PID Tuning
# Kp=120 (1.20), Ki=80 (0.80), Kd=1 (0.01)
```

Monitor encoder feedback over UDP telemetry (port 9999) to visualize step response.

### 2. Ultrasonic Obstacle Avoidance

The 4 ultrasonic sensors (front, back, left, right) trigger emergency stop at 5cm. Write custom avoidance logic:

```c
// In your main loop, read ultrasonic distances:
float front_dist = ultrasonic_get_range_m(US_FRONT);
if (front_dist < 0.20f) {
    // Turn away from obstacle
    motor_mecanum_drive(&(cmd_vel_t){.vx=0, .vy=0, .omega=1.0f});
}
```

### 3. FreeRTOS Multi-tasking

The firmware uses FreeRTOS tasks for concurrent operation:

| Task | Priority | Stack | Function |
|------|----------|-------|----------|
| Motor control | 5 | 4096 | PID loop at 50Hz |
| Ultrasonic scan | 3 | 2048 | Sensor polling |
| WiFi/UDP | 2 | 4096 | Command reception |
| Battery monitor | 1 | 2048 | Voltage sampling |

Create your own tasks to experiment with priorities, queues, and semaphores.

### 4. Encoder Odometry

Read wheel encoders to estimate robot position:

```c
// Each encoder gives pulses via PCNT hardware
int32_t fl_count = encoder_get_count(MOTOR_FL);
float fl_rps = encoder_get_speed_rps(MOTOR_FL);  // revolutions/second

// Convert to linear velocity:
// v = rps * 2π * wheel_radius
float v_fl = fl_rps * 2.0f * 3.14159f * 0.024f;  // 24mm radius
```

## Upgrading to Standard SKU

When ready for autonomous navigation, add a Raspberry Pi 5 and the Standard SKU software stack. The ESP32 firmware remains the same — it communicates with the Pi 5 over UART using micro-ROS.
