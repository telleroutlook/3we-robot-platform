# Firmware Guide

Complete guide for building, flashing, configuring, and debugging the ESP32-S3 firmware.

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
# Source ESP-IDF environment
. $HOME/esp/esp-idf/export.sh

cd firmware/esp32

# Set target chip
idf.py set-target esp32s3

# (Optional) Configure options
idf.py menuconfig

# Build (default SKU: standard)
idf.py build
```

### SKU Variants

Available: `basic`, `standard`, `pro`, `industrial`

```bash
# Build specific SKU variant
cp ../config/sdkconfig.defaults.pro sdkconfig.defaults
idf.py fullclean && idf.py build
```

### Host-Side Unit Tests (no hardware needed)

```bash
cd firmware/tests
make clean && make
./test_runner
```

---

## Flash

### Connection

Connect USB-C cable between your computer and the ESP32-S3 programming port.

If using UART header instead:
- TX -> USB-UART adapter RX
- RX -> USB-UART adapter TX
- GND -> GND
- Hold BOOT button during reset to enter download mode

### Flash Command

```bash
idf.py -p /dev/ttyUSB0 flash
```

Port names by platform:
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
I (xxx) safety: Safety system initialized (E-stop GPIO=41)
I (xxx) motor: Motor control initialized (20000 Hz PWM, 8-bit)
I (xxx) encoder: Encoders initialized (PCNT, 1440 CPR)
I (xxx) ultrasonic: Ultrasonic sensors initialized (trig=12)
I (xxx) imu: BNO055 initialized (addr=0x28, NDOF mode)
I (xxx) battery: Battery ADC initialized (2S, divider=3.0)
I (xxx) uros: micro-ROS initialized (UART 921600 baud)
I (xxx) main: All systems initialized. Robot ready.
```

Exit monitor: `Ctrl+]`

### Filtering Logs

```bash
idf.py monitor --filter "safety"
idf.py monitor --filter "uros"
```

---

## Configuration (menuconfig)

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

## micro-ROS Agent Setup (Raspberry Pi)

```bash
# Install (one-time)
sudo apt install ros-humble-micro-ros-agent

# Run agent (serial transport)
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyAMA0 -b 921600

# Or UDP transport (if configured in firmware)
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

### Verify Communication

```bash
ros2 topic list

# Expected topics:
#   /odom
#   /ultrasonic/front, /back, /left, /right
#   /battery_state
#   /wheel_speeds
#   /cmd_vel

ros2 topic echo /odom

ros2 topic pub /cmd_vel geometry_msgs/Twist \
  "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {z: 0.0}}"
```

---

## OTA Update

Over-the-air firmware updates via ESP-IDF's native OTA mechanism:

1. Build firmware binary: `idf.py build`
2. Sign with Ed25519 key: `espsecure.py sign_data --keyfile private.pem build/robot_platform_firmware.bin`
3. Upload signed binary to OTA server
4. Trigger update via ROS2 service or HTTP endpoint

OTA requires two OTA partitions and secure boot. See [fleet_ota_strategy.md](fleet_ota_strategy.md) for production deployment.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No serial port found` | USB not connected or driver missing | Check cable, install driver |
| `Failed to connect` | ESP32 not in download mode | Hold BOOT, press RESET, release BOOT |
| `micro-ROS agent: no subscriber` | UART wiring issue | Check TX/RX crossover, verify baud rate |
| `BNO055 not found` | I2C connection issue | Check SDA/SCL wiring, pull-ups |
| `Watchdog timeout` | Control loop stalled | Check for infinite loops, stack overflow |
