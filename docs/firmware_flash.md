# Firmware Build and Flash Guide

Instructions for building and flashing the ESP32-S3 firmware.

## Prerequisites

### ESP-IDF Installation

Install ESP-IDF v5.x following the [official guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/):

```bash
mkdir -p ~/esp
cd ~/esp
git clone -b v5.2 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32s3
source export.sh
```

### micro-ROS Component

The firmware depends on [micro-ROS for ESP32](https://github.com/micro-ROS/micro_ros_espidf_component). It will be fetched automatically by the ESP-IDF component manager on first build.

### USB Driver

- **Linux**: No driver needed (CP2102 supported by kernel)
- **macOS**: Install [Silicon Labs CP210x driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
- **Windows**: Install CP210x Universal Driver from Silicon Labs

---

## Build

```bash
cd firmware/esp32

# Set target chip
idf.py set-target esp32s3

# (Optional) Configure options
idf.py menuconfig
# Navigate to: Robot Platform Configuration
#   - Select SKU variant
#   - Set Wi-Fi credentials
#   - Adjust PID gains if needed

# Build
idf.py build
```

Expected output:
```
Project build complete. To flash, run this command:
  idf.py -p (PORT) flash
```

Build artifacts are in `firmware/esp32/build/`.

---

## Flash

### Connection

Connect USB-C cable between your computer and the ESP32-S3 programming port.

If using UART header instead:
- TX → USB-UART adapter RX
- RX → USB-UART adapter TX
- GND → GND
- Hold BOOT button during reset to enter download mode

### Flash Command

```bash
idf.py -p /dev/ttyUSB0 flash
```

Replace `/dev/ttyUSB0` with your actual port:
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`
- macOS: `/dev/cu.usbserial-*` or `/dev/cu.SLAB_USBtoUART`
- Windows: `COM3` (check Device Manager)

### Monitor

```bash
idf.py -p /dev/ttyUSB0 monitor
```

Expected boot messages:
```
I (xxx) main: Robot Platform Firmware starting...
I (xxx) safety: Safety system initialized (E-stop GPIO=36)
I (xxx) motor: Motor control initialized (20000 Hz PWM, 8-bit)
I (xxx) encoder: Encoders initialized (PCNT, 1440 CPR)
I (xxx) ultrasonic: Ultrasonic sensors initialized (trig=12)
I (xxx) imu: BNO055 initialized (addr=0x28, NDOF mode)
I (xxx) battery: Battery ADC initialized (2S, divider=3.0)
I (xxx) uros: micro-ROS initialized (UART 921600 baud)
I (xxx) main: All systems initialized. Robot ready.
```

Exit monitor: `Ctrl+]`

---

## micro-ROS Agent Setup (Raspberry Pi)

On the Raspberry Pi 5, install and run the micro-ROS agent:

```bash
# Install (one-time)
sudo apt install ros-humble-micro-ros-agent

# Run agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyAMA0 -b 921600
```

### Verify Communication

In another terminal:
```bash
# List topics (should show firmware publishers)
ros2 topic list

# Expected topics:
#   /odom
#   /ultrasonic/front
#   /ultrasonic/back
#   /ultrasonic/left
#   /ultrasonic/right
#   /battery_state
#   /wheel_speeds
#   /cmd_vel

# Echo odometry
ros2 topic echo /odom

# Send a velocity command
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {z: 0.0}}"
```

---

## Configuration via menuconfig

Key options in `Robot Platform Configuration`:

| Option | Default | Description |
|--------|---------|-------------|
| Robot SKU | Basic | Enables/disables SKU-specific features |
| Motor PID Kp | 1.20 | Proportional gain |
| Motor PID Ki | 0.80 | Integral gain |
| Motor PID Kd | 0.01 | Derivative gain |
| Wi-Fi SSID | robot-platform | AP mode SSID |
| micro-ROS baud | 921600 | UART communication speed |
| cmd_vel timeout | 500ms | Motor stop timeout |
| Safety distance | 5cm | Ultrasonic E-stop threshold |

---

## OTA Update (Future)

Over-the-air firmware updates via ESP-IDF's native OTA mechanism:

1. Build firmware binary: `idf.py build`
2. Sign with Ed25519 key: `espsecure.py sign_data --keyfile private.pem build/robot_platform_firmware.bin`
3. Upload signed binary to OTA server
4. Trigger update via ROS2 service or HTTP endpoint

**Note**: OTA requires the firmware to be built with two OTA partitions and secure boot enabled. This is planned for v0.2.0.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No serial port found` | USB not connected or driver missing | Check cable, install driver |
| `Failed to connect` | ESP32 not in download mode | Hold BOOT, press RESET, release BOOT |
| `micro-ROS agent: no subscriber` | UART wiring issue | Check TX/RX crossover, verify baud rate |
| `BNO055 not found` | I2C connection issue | Check SDA/SCL wiring, pull-ups |
| `Watchdog timeout` | Control loop stalled | Check for infinite loops, stack overflow |
