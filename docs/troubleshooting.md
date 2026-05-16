# Troubleshooting Guide

Organized by symptom. Start with the most likely cause and work through diagnostics.

## Robot Won't Move

### Symptom: No motor response to /cmd_vel commands

**1. E-stop is active**

```bash
ros2 topic echo /emergency_stop_state --once
# Check: stopped=true → E-stop active
```

Resolution: Release the physical E-stop button. The safety state machine requires hardware acknowledgment before recovery.

**2. No micro-ROS connection**

```bash
ros2 topic list
# If /odom is missing, micro-ROS agent is not bridging
```

Resolution:
- Verify micro-ROS agent is running: `ps aux | grep micro_ros_agent`
- Check serial cable connection between RPi and ESP32
- Verify baud rate: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 921600`

**3. Watchdog timeout**

If no `/cmd_vel` arrives for 500ms, motors stop automatically. Verify your publisher rate:

```bash
ros2 topic hz /cmd_vel
# Should be >= 10 Hz
```

**4. Safety speed limit is zero**

The speed limit is stored in NVS. If corrupted, it may clamp all speeds to zero:

```bash
# Check via serial monitor for:
# "speed_limit = 0.00"
```

Resolution: Re-flash firmware or reset NVS partition.

**5. Motor wiring reversed**

If one wheel spins the wrong direction, swap IN1/IN2 wires for that motor, or negate the pin assignment in `firmware/config/pin_definitions.h`.

---

## No ROS Topics Visible

### Symptom: `ros2 topic list` shows nothing or only /rosout

**1. micro-ROS agent not running**

```bash
# Start the agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 --baudrate 921600
```

**2. Wrong serial device**

```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Try each device until topics appear
```

**3. Firmware not running**

Connect to serial monitor (115200 baud for ESP32 console, separate from micro-ROS UART):
```bash
idf.py -p /dev/ttyUSB0 monitor
# Look for "micro-ROS initialized" message
```

**4. ROS2 environment not sourced**

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

**5. DDS domain mismatch**

```bash
echo $ROS_DOMAIN_ID
# Should be unset (default 0) or matching across all nodes
```

---

## Web UI Can't Connect

### Symptom: Web control shows "Disconnected" or "Error"

**1. Rosbridge not running**

```bash
ros2 node list | grep rosbridge
# Should show /rosbridge_websocket
```

Start it: `ros2 launch rosbridge_server rosbridge_websocket_launch.xml`

**2. Wrong URL in browser**

Default: `ws://<robot-ip>:9090`

- Verify robot IP: `hostname -I` on the companion computer
- Verify port 9090 is open: `ss -tlnp | grep 9090`

**3. Firewall blocking WebSocket**

```bash
sudo ufw status
# If active, allow port 9090:
sudo ufw allow 9090/tcp
```

**4. Browser on different network**

The browser must be on the same network as the robot. Check that your device's Wi-Fi is connected to the robot's network.

**5. Mixed content (HTTPS page + WS)**

If serving the web UI over HTTPS, the WebSocket must also be secure (wss://). Use a reverse proxy with TLS, or serve the page over HTTP during development.

---

## Battery Reading Incorrect

### Symptom: Voltage doesn't match multimeter measurement

**1. Voltage divider resistor mismatch**

The firmware assumes a 3.0x divider ratio (10kΩ + 20kΩ). Verify physical resistor values with a multimeter.

Expected: ADC reads V_batt / 3.0, firmware multiplies back.

**2. ADC calibration drift**

```bash
ros2 topic echo /battery_state --once
# Compare .voltage field to multimeter reading
```

If consistently off by a fixed ratio, adjust `BATT_VOLTAGE_DIVIDER` in `firmware/config/robot_params.h`.

**3. Noisy readings**

The firmware averages 8 samples. If still noisy, check for:
- Poor solder joint on ADC pin
- Missing decoupling capacitor
- Motor noise coupling into ADC trace

---

## E-Stop Won't Reset

### Symptom: Robot stays in E-stop state after button release

**1. Physical button still pressed**

Verify the button has actually been released. Check the GPIO level:
- Serial monitor shows `safety_state: ESTOPPED` → button still active
- `safety_state: RECOVERY_PENDING` → button released, awaiting confirmation

**2. Relay feedback fault**

If the relay welded shut or the feedback line is broken:
```
# Serial output:
"RELAY FAULT: relay energized while E-stopped - possible welded contact"
"RELAY FAULT ESCALATED: welded contact confirmed - service required"
```

Resolution: After physical repair, use `safety_clear_relay_fault()` (exposed via ROS2 service or DTLS command) to clear the persistent fault flag in NVS. The system transitions to ESTOPPED, then requires normal reset flow.

**3. RECOVERY_PENDING state stuck**

If reset was initiated but confirmation never arrived (10s timeout reverts to ESTOPPED):
```
# Serial output:
"RECOVERY_PENDING timeout (10000ms) - reverting to ESTOPPED"
```

Resolution: Retry the reset flow. Ensure the client sending `safety_confirm_reset()` is connected and responsive.

**4. Software E-stop recovery**

Software-triggered E-stops follow a two-step recovery:
1. Call `safety_reset()` — requires physical button released, transitions to RECOVERY_PENDING
2. Call `safety_confirm_reset()` within 10 seconds — transitions to NORMAL

No power cycle required. This is a deliberate two-step handshake to prevent accidental re-arming.

**4. Watchdog fault latched**

If the control loop stalled and triggered the watchdog, the firmware enters E-stop. After fixing the cause, power cycle the robot.

---

## Firmware Won't Flash

### Symptom: `idf.py flash` fails

**1. Wrong serial port**

```bash
ls /dev/ttyUSB* /dev/cu.usbserial-*
# Try: idf.py -p /dev/ttyUSB0 flash
```

**2. ESP32 not in download mode**

Hold BOOT button while pressing RESET, then release BOOT. Some boards auto-enter download mode.

**3. Permission denied**

```bash
sudo chmod 666 /dev/ttyUSB0
# Or add user to dialout group:
sudo usermod -aG dialout $USER
# Then log out and back in
```

**4. IDF_PATH not set**

```bash
. $HOME/esp/esp-idf/export.sh
echo $IDF_PATH  # Should print the path
```

**5. Wrong target**

```bash
idf.py set-target esp32s3
# Must match the actual chip (esp32s3, not esp32 or esp32c3)
```

---

## Ultrasonic Sensor Issues

### Symptom: All readings show max range (4.0m) or zero

**1. Wiring**

- Trigger pin is shared (GPIO as defined in `pin_definitions.h`)
- Each sensor has its own echo pin
- Verify VCC is 5V (not 3.3V) for HC-SR04

**2. RMT channel conflict**

If other peripherals use RMT channels, check for conflicts in `sdkconfig`.

**3. Echo pin not connected**

```bash
ros2 topic echo /ultrasonic/front --once
# If range == max_range consistently, echo signal not received
```

**4. Object too close**

Minimum range is 2cm. Objects closer than 2cm may read as max range.

---

## Payload Not Detected

### Symptom: PayloadState shows connected=false with payload plugged in

**1. EEPROM not programmed**

The payload must have a valid EEPROM descriptor at I2C address 0x50:
```bash
eeprom-validator verify <eeprom_file.bin>
```

**2. I2C bus issue**

- Check SDA/SCL pull-up resistors (4.7kΩ to 3.3V)
- Verify I2C address with `i2cdetect`:
  ```bash
  i2cdetect -y 1  # On RPi, or check ESP32 serial logs
  ```

**3. Power sequencing**

The platform waits 300ms after detection before EEPROM read. If the payload needs longer to initialize, it may fail the first read.

---

## Common ROS2 Debugging Commands

```bash
# List all active topics
ros2 topic list

# Check message rate
ros2 topic hz /odom

# View single message
ros2 topic echo /battery_state --once

# Check node health
ros2 node info /robot_base

# List available services
ros2 service list

# Call emergency stop
ros2 service call /emergency_stop robot_interfaces/srv/EmergencyStop "{reason: 'test'}"

# System diagnostics
ros2 doctor --report

# Check TF tree
ros2 run tf2_tools view_frames
```

## Serial Monitor Quick Reference

```bash
# ESP32 console (logs, debug output)
idf.py -p /dev/ttyUSB0 monitor

# Key log tags to filter:
#   [safety]  — E-stop, watchdog, relay state
#   [uros]    — micro-ROS connection
#   [motor]   — PWM commands
#   [batt]    — Battery readings
#   [us]      — Ultrasonic measurements
#   [dtls]    — DTLS handshake, session info
#   [payload] — Hot-plug detection
```
