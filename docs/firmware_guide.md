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

Available: `basic`, `standard`, `industrial`

```bash
# Build specific SKU variant (from firmware/esp32/ directory)
cp sdkconfig.defaults.industrial sdkconfig.defaults
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
I (xxx) charging: Charging detect initialized (threshold=2000mV)
I (xxx) heartbeat: Heartbeat monitor initialized (timeout=5000ms)
I (xxx) ext_wdt: External watchdog feeder started (500ms period)
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
2. Sign with ECDSA P-256 key (see `firmware/esp32/main/ota_signing.h` for format)
3. Upload signed binary to OTA server
4. Trigger update via ROS2 service or HTTP endpoint

OTA requires two OTA partitions and secure boot. See [fleet_ota_strategy.md](fleet_ota_strategy.md) for production deployment.

### Pre-flight Checks

Before an OTA update is accepted, the firmware runs an automated pre-flight validation (`ota_preflight.c`):

| Check | Threshold | Rationale |
|-------|-----------|-----------|
| Battery | ≥ 50% | Prevent power loss during flash |
| Wi-Fi RSSI | ≥ -70 dBm | Ensure stable download |
| Motors | Idle | No active motion commands |
| Thermal | < warning | Prevent overtemp during heavy CPU use |
| Safety | Not triggered | E-stop must be cleared |

If any check fails, the OTA is rejected with a `fail_reason` string.

### Validation Window

After a successful OTA boot, a 30-second validation window starts. If the firmware does not confirm itself within this period (or if 3 consecutive boot failures occur), the bootloader automatically rolls back to the previous partition.

### Compatibility Matrix

The OTA compatibility module (`ota_compat.c`) enforces protocol version gating. A new firmware image declares a minimum and maximum compatible firmware version, preventing downgrades below the protocol break point.

---

## Heartbeat Monitor

The heartbeat monitor (`heartbeat_monitor.c`) expects periodic messages from the companion computer (Raspberry Pi). If no heartbeat arrives within 5 seconds:

1. Motors are commanded to zero
2. After 3 consecutive resets within 30 minutes, the safety relay is pulsed off for 3 seconds (hardware-level stop)

This ensures the robot stops if the companion computer crashes or the serial link is severed.

---

## External Watchdog

An external TPS3813 hardware watchdog IC provides a last-resort reset if the ESP32 firmware hangs. The `external_wdt.c` module toggles GPIO 46 at 1 Hz (500ms period). If toggling stops, the TPS3813 triggers a hardware reset.

---

## Charging Contact Detection

The `charging_detect.c` module monitors a pogo-pin voltage on ADC1_CH8 (GPIO 9). It uses the ESP32-S3 curve-fitting calibration scheme for accurate millivolt conversion.

| Parameter | Value |
|-----------|-------|
| ADC channel | ADC1_CH8 (GPIO 9) |
| Attenuation | 12 dB (0–3.3V range) |
| Contact threshold | 2000 mV |
| Calibration | Curve fitting (ESP32-S3) |

`charging_detect_is_connected()` returns `true` when the voltage exceeds the threshold, indicating the robot is seated on a charging dock.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `No serial port found` | USB not connected or driver missing | Check cable, install driver |
| `Failed to connect` | ESP32 not in download mode | Hold BOOT, press RESET, release BOOT |
| `micro-ROS agent: no subscriber` | UART wiring issue | Check TX/RX crossover, verify baud rate |
| `BNO055 not found` | I2C connection issue | Check SDA/SCL wiring, pull-ups |
| `Watchdog timeout` | Control loop stalled | Check for infinite loops, stack overflow |
