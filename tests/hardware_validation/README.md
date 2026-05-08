# Hardware Validation Test Plan

## Overview

Systematic verification of the robot platform prototype. Each subsystem is tested independently before full integration.

## Prerequisites

- Assembled prototype (Standard SKU BOM)
- ESP32-S3 flashed with latest firmware
- micro-ROS agent running on host: `ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888`
- ROS2 Humble installed on host
- Multimeter for voltage verification

## Test Sequence

Execute tests in order — later tests depend on earlier ones passing.

### 1. Power-On and Safety System

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Apply power with E-stop pressed | No motor power, relay LED off | [ ] |
| 1.2 | Release E-stop | Relay energizes, feedback LED on | [ ] |
| 1.3 | `safety_relay_selftest()` log | "Relay self-test PASSED" in serial | [ ] |
| 1.4 | Press E-stop during operation | Motors stop immediately (<50ms) | [ ] |
| 1.5 | Software E-stop via service | `ros2 service call /emergency_stop` stops motors | [ ] |
| 1.6 | Reset after E-stop released | `safety_reset()` succeeds | [ ] |
| 1.7 | Watchdog timeout | Stop sending /cmd_vel for 1s → motors stop | [ ] |

### 2. Motor Direction Verification

| # | Motor | Command | Expected Direction |
|---|-------|---------|-------------------|
| 2.1 | FL | speed = +1.0 | Forward (away from robot) |
| 2.2 | FR | speed = +1.0 | Forward |
| 2.3 | RL | speed = +1.0 | Forward |
| 2.4 | RR | speed = +1.0 | Forward |
| 2.5 | All | vx = +0.2 | Robot moves forward |
| 2.6 | All | vy = +0.2 | Robot strafes left |
| 2.7 | All | omega = +0.5 | Robot rotates CCW |

Use `scripts/motor_sweep.py` for individual motor testing.

### 3. Encoder Verification

| # | Test | Expected |
|---|------|----------|
| 3.1 | Rotate FL wheel 1 revolution by hand | Count delta ≈ 1440 (±5%) |
| 3.2 | Rotate FR wheel 1 revolution | Count delta ≈ 1440 |
| 3.3 | Verify direction: forward rotation = positive delta | Positive count |
| 3.4 | Run motor at 50% for 2s, check speed_rps | Non-zero, reasonable value |

Use `scripts/encoder_calibrate.py` for data logging.

### 4. Ultrasonic Sensors

| # | Test | Expected |
|---|------|----------|
| 4.1 | Front sensor, no obstacle | Reading > 2.0m (or max range) |
| 4.2 | Front sensor, obstacle at 30cm | Reading = 0.28–0.32m |
| 4.3 | Front sensor, obstacle at 5cm | Reading ≈ 0.05m |
| 4.4 | All 4 sensors operational | No timeout errors in log |
| 4.5 | Emergency stop at <5cm threshold | Motors stop when obstacle < US_SAFETY_THRESHOLD_M |

Use `scripts/ultrasonic_log.py` for data recording.

### 5. IMU (BNO055)

| # | Test | Expected |
|---|------|----------|
| 5.1 | Robot flat on table | Roll ≈ 0°, Pitch ≈ 0° |
| 5.2 | Tilt forward 45° | Pitch ≈ 45° |
| 5.3 | Tilt left 45° | Roll ≈ 45° |
| 5.4 | Rotate 90° CW | Yaw changes by ~90° |
| 5.5 | Calibration status | All sensors show calibrated (3/3) |

### 6. Battery Monitoring

| # | Test | Expected |
|---|------|----------|
| 6.1 | Measure battery with multimeter | Note actual voltage |
| 6.2 | Compare to ADC reading | Within ±0.1V of multimeter |
| 6.3 | Percentage at full charge | ~100% |
| 6.4 | Low voltage simulation | Warning log at 3.3V/cell |
| 6.5 | Critical voltage | BATT_CRITICAL state triggered |

### 7. Payload Hotplug

| # | Test | Expected |
|---|------|----------|
| 7.1 | No payload connected | PayloadState: not_connected |
| 7.2 | Connect payload with EEPROM | Detection within 500ms, descriptor parsed |
| 7.3 | Enable 5V rail | Payload 5V measured at connector |
| 7.4 | Enable 12V rail | Payload 12V measured at connector |
| 7.5 | Disconnect payload | State returns to not_connected, rails disabled |

### 8. Communication (micro-ROS)

| # | Test | Expected |
|---|------|----------|
| 8.1 | Agent connection | "micro-ROS agent connected" in log |
| 8.2 | Topic publication | `ros2 topic list` shows /odom, /battery_state, etc. |
| 8.3 | Command reception | Publish to /cmd_vel → motors respond |
| 8.4 | Disconnect/reconnect | Agent restart → auto-reconnects |

### 9. Full Integration — Mecanum Drive

| # | Test | Expected |
|---|------|----------|
| 9.1 | Joystick forward | Straight-line motion |
| 9.2 | Joystick lateral | Pure strafing (no rotation) |
| 9.3 | Joystick diagonal | 45° motion |
| 9.4 | Rotation | Spin in place |
| 9.5 | Combined translation + rotation | Smooth arc |
| 9.6 | Speed limit respected | Max velocity ≤ safety_get_speed_limit() |

## Failure Response

- **Safety tests fail**: DO NOT proceed. Debug hardware wiring first.
- **Motor direction wrong**: Swap IN1/IN2 wires OR negate in pin_definitions.h
- **Encoder count wrong**: Check A/B phase wiring, verify CPR with known rotation
- **ADC reading off**: Verify voltage divider resistor values physically
