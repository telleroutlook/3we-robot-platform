# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2025-05-09

### Added

- Complete ESP32-S3 firmware: motor control (DRV8833 PWM), encoder (PCNT), IMU (BNO055), ultrasonic (RMT), battery monitoring, thermal protection
- Safety module: hardware E-stop relay, software watchdog, speed limiter, relay self-test
- DTLS 1.2 encrypted control channel (PSK authentication, port 5684)
- OTA firmware signing (ECDSA P-256) with bootloader verification
- Industrial SKU CAN bus support
- micro-ROS DDS-XRCE communication layer (UART 921600 baud)
- UDP plaintext telemetry fallback (port 5685)
- ROS2 workspace with 4 packages:
  - `robot_interfaces` — 3 messages (WheelSpeeds, EmergencyStopState, PayloadState) and 2 services (EmergencyStop, PayloadPower)
  - `robot_description` — URDF/Xacro for mecanum platform with 4 ultrasonic sensors, IMU, payload mount
  - `robot_bringup` — Launch files for hardware, navigation (Nav2 + slam_toolbox), QoS profiles
  - `robot_simulation` — Gazebo Fortress environment with sensor plugins, obstacle worlds, RViz config
- Nav2 configuration tuned for mecanum omnidirectional drive (DWB local planner with lateral velocity)
- PBC-34 Payload Interface SDK (Python):
  - `PayloadDescriptor` frozen dataclass with EEPROM parsing
  - `PayloadInterface` I2C communication with CRC-16/MODBUS framing
  - Capability flags module (I2C, SPI, UART, GPIO, ADC, PWM, CAN)
  - EEPROM validator CLI tool
  - Example payloads (hello_payload, sensor_payload)
- Web control interface (Lit + TypeScript + Vite):
  - 7 Web Components: joystick, battery-gauge, sensor-radar, estop-button, imu-attitude, wheel-speeds, payload-panel
  - ROS bridge WebSocket connection manager
  - Zod schema validation for incoming messages
- Minimal web_basic fallback interface (zero dependencies, plain HTML/JS)
- Hardware design:
  - KiCad 8 PCB schematic and layout (DRV8833, ESP32-S3, power management, PBC-34 connector)
  - Custom footprint library (PBC-34, XT30)
  - 7 DXF mechanical drawings (chassis, motor bracket, payload plate)
  - 4 SKU BOMs (basic, standard, pro, industrial)
  - DRC validation scripts and Gerber generation
- 23 firmware unit tests (Unity framework, host-side compilation)
- Playwright E2E test suite for web_control (7 spec files)
- pytest suite for payload SDK (protocol, EEPROM validator, capability flags)
- `validate-ros-types.ts` cross-layer type synchronization script
- GitHub Actions CI:
  - Firmware build and test (ESP-IDF)
  - ROS2 build (colcon)
  - Python lint (ruff) and tests (pytest)
  - Web control tests (Playwright)
  - Hardware DRC check
- CLA/DCO enforcement workflows
- 13 documentation guides: assembly, firmware flash, payload development, ROS2 interface reference, network architecture, web control API, rosbridge guide, performance benchmarks, troubleshooting, compliance checklist, SLAM alternatives, hardware rendering prompts
- Bilingual README (English + Chinese)
- CONTRIBUTING.md with branch strategy, commit conventions, safety review requirements
- DEVELOPMENT.md with per-subsystem workflows and validation checklist
- Triple license structure: Apache-2.0 (code), CERN-OHL-P-2.0 (hardware), CC-BY-SA-4.0 (docs)
- `setup-dev-env.sh` environment setup with OS detection
- `flash-firmware.sh` automated flashing
- `package-release.sh` release artifact bundling
- `run-hardware-validation.py` physical robot test orchestration

### Changed

- EmergencyStop service extended with `STATE_RELAY_FAULT` constant (4 states total)
- `PayloadDescriptor` made frozen (immutable dataclass)
- `PayloadInterface` supports context manager protocol (`with` statement)

### Fixed

- 18 critical/high security vulnerabilities from initial code review
- 14 safety-critical correctness issues (motor control, encoder overflow, watchdog timing)
- 22 safety, correctness, and security issues across firmware, SDK, and ROS2
- 30 issues from full-repository code review pass
- Pre-existing build errors in test infrastructure
- 4 code quality improvements in firmware and SDK

### Security

- Pinned CI workflow dependencies with hash verification
- DTLS transport hardened: cookie-based DoS protection, AEAD-only cipher suites
- OTA binary signing enforced at bootloader level (rejects unsigned images)
- Payload code sandboxing (cannot access motor control, safety circuits, or core config)
- Control commands over wireless require DTLS encryption (no plaintext motor control)
