# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **ROS2 — `robot_collection` package**: Autonomous ball collection demo with state machine orchestrating camera, robotic arm + vacuum pump, and tipping basket payloads. Nodes: `collection_manager`, `ball_tracker`, `arm_controller`, `basket_controller`
- **ROS2 — `ball_detector` node** (`robot_perception`): HSV color detection with HoughCircles fallback for ping-pong ball detection
- **ROS2 — CollectBalls action** (`robot_interfaces/action/CollectBalls`): Main task action for autonomous ball collection
- **ROS2 — CollectionState message** (`robot_interfaces/msg/CollectionState`): 6-stage state machine feedback (IDLE → SEARCHING → APPROACHING → PICKING → RETURNING → DUMPING)
- **ROS2 — ArmCommand service** (`robot_interfaces/srv/ArmCommand`): Arm position + vacuum pump control
- **ROS2 — BasketDump service** (`robot_interfaces/srv/BasketDump`): Basket tipping control
- **Web — `<robot-collection-status>`**: Real-time collection state display with stage badges, statistics, and start/stop controls
- **Launch — `collection_demo.launch.py`**: Combined launch for all collection subsystems via `robot_bringup`
- **Firmware — Capability flags update**: Added `CAP_CAMERA` (bit 7), reassigned `CAP_CAN` to bit 6 in `payload_hotplug.c`
- **Firmware — OTA Pre-flight Checks**: Battery ≥50%, Wi-Fi RSSI ≥-70 dBm, motors idle, thermal OK, safety not triggered. 30-second validation window after boot; auto-rollback after 3 consecutive boot failures (`ota_preflight.c`)
- **Firmware — OTA Compatibility Matrix**: Protocol version gate prevents incompatible firmware from being applied (`ota_compat.c`)
- **Firmware — Heartbeat Monitor**: 5-second timeout on Raspberry Pi heartbeat. Triggers graceful motor shutdown and safety relay pulse after 3 consecutive resets within 30 minutes (`heartbeat_monitor.c`)
- **Firmware — External Watchdog**: TPS3813 hardware watchdog feeder task (200ms toggle on GPIO 46, 8× margin vs 1.6s timeout). Stops toggling = hardware reset (`external_wdt.c`)
- **Firmware — Charging Contact Detection**: ADC-based pogo pin voltage sense on ADC1_CH8. Uses curve-fitting calibration for ESP32-S3. Threshold 2.0V for contact detection (`charging_detect.c`)
- **Firmware — Multi-pack Battery Support**: Extended battery module with configurable cell count (2S–6S) and per-cell threshold lookup
- **ROS2 — `robot_docking` package**: Autonomous docking controller with visual servo (ArUco marker), contact verification via charging ADC, and staged state machine (IDLE → APPROACH → VISUAL_SERVO → CONTACT_VERIFY → DOCKED)
- **ROS2 — Dock action** (`robot_interfaces/action/Dock`): Navigate to and dock at a named charging station with progress feedback
- **ROS2 — DockingState message** (`robot_interfaces/msg/DockingState`): 8-stage docking state with distance estimate
- **ROS2 — UndockRobot service** (`robot_interfaces/srv/UndockRobot`): Reverse out of dock with configurable distance
- **ROS2 — Health Monitor Node** (`robot_diagnostics/health_monitor_node.py`): Aggregates battery, thermal, connectivity, and topic rate health with configurable thresholds
- **Gazebo headless mode**: `headless:=true` launch argument runs simulation in server-only mode (`-s` flag), suppresses RViz2 in CI
- **CI — Integration tests in simulation**: Diagnostics node tests (battery, safety/E-stop) run in Gazebo headless with `QT_QPA_PLATFORM=offscreen`

### Changed

- `pin_definitions.h`: `CHARGE_ADC_ATTEN` uses `ADC_ATTEN_DB_11` (ESP-IDF 5.x naming; the deprecated `ADC_ATTEN_DB_12` constant from ESP-IDF 4.x is no longer referenced)
- `charging_detect.c`: Switched from `adc_cali_line_fitting` (ESP32 only) to `adc_cali_curve_fitting` (ESP32-S3 compatible)
- `gazebo.launch.py`: Added `headless` launch argument; RViz2 auto-suppressed when headless
- Integration test `test_diagnostics_reports_estop`: Publishes E-stop message multiple times with spin to prevent DDS discovery race

### Fixed

- Firmware build failure: ESP32-S3 does not support `adc_cali_line_fitting` scheme (only curve fitting)
- ROS2 Build workflow: `hashFiles()` syntax error (comma-separated patterns in single string)
- Integration tests: Gazebo and RViz2 crash on `xcb` display connection in headless CI
- Integration tests: E-stop diagnostics test race condition (single-publish before DDS discovery)
- Full Validation workflow: `dtls_authority.c` linker error (missing from CMakeLists.txt)

## [0.1.0] - 2025-05-09

### Added

- Complete ESP32-S3 firmware: motor control (DRV8833 PWM), encoder (PCNT), IMU (BNO055), ultrasonic (RMT), battery monitoring, thermal protection
- Safety module: hardware E-stop relay, software watchdog, speed limiter, relay self-test
- DTLS 1.2 encrypted control channel (PSK authentication, port 5684)
- OTA firmware signing (ECDSA P-256) with bootloader verification
- Industrial SKU CAN bus support
- micro-ROS DDS-XRCE communication layer (UART 921600 baud)
- UDP plaintext telemetry fallback (cmd port 8888, telemetry port 9999)
- ROS2 workspace with 8 packages:
  - `robot_interfaces` — 4 messages (WheelSpeeds, EmergencyStopState, PayloadState, DockingState), 3 services (EmergencyStop, PayloadPower, UndockRobot), 1 action (Dock)
  - `robot_description` — URDF/Xacro for mecanum platform with 4 ultrasonic sensors, IMU, payload mount
  - `robot_bringup` — Launch files for hardware, navigation (Nav2 + slam_toolbox), QoS profiles
  - `robot_simulation` — Gazebo Fortress environment with sensor plugins, obstacle worlds, RViz config
  - `robot_diagnostics` — Health monitoring and diagnostics aggregator
  - `robot_docking` — Autonomous docking controller with visual servo
  - `robot_perception` — Camera + AI inference (Hailo accelerator)
  - `robot_competition` — RoboCup Logistics League competition nodes
- Nav2 configuration tuned for mecanum omnidirectional drive (DWB local planner with lateral velocity)
- PBC-34 Payload Interface SDK (Python):
  - `PayloadDescriptor` frozen dataclass with EEPROM parsing
  - `PayloadInterface` I2C communication with CRC-16/MODBUS framing
  - Capability flags module (I2C, SPI, UART, GPIO, ADC, PWM, CAN)
  - EEPROM validator CLI tool
  - Example payloads (hello_payload, sensor_payload)
- Web control interface (TypeScript Web Components + Vite):
  - 8 Web Components: joystick, battery-gauge, sensor-radar, estop-button, imu-attitude, wheel-speeds, payload-panel, system-status
  - ROS bridge WebSocket connection manager with exponential backoff reconnect
  - Zod schema validation for incoming messages
- Minimal web_basic fallback interface (zero dependencies, plain HTML/JS)
- Hardware design:
  - KiCad 8 PCB schematic and layout (DRV8833, ESP32-S3, power management, PBC-34 connector)
  - Custom footprint library (PBC-34, XT30)
  - 7 DXF mechanical drawings (chassis, motor bracket, payload plate)
  - 3 SKU BOMs (basic, standard, industrial) + optional add-ons
  - DRC validation scripts and Gerber generation
- 26 firmware unit tests (Unity framework, host-side compilation)
- Playwright E2E test suite for web_control (8 spec files)
- pytest suite for payload SDK (protocol, EEPROM validator, capability flags)
- `validate-ros-types.ts` cross-layer type synchronization script
- GitHub Actions CI:
  - Firmware build and test (ESP-IDF)
  - ROS2 build (colcon)
  - Python lint (ruff) and tests (pytest)
  - Web control tests (Playwright)
  - Hardware DRC check
- CLA/DCO enforcement workflows
- 19 documentation guides: assembly, firmware flash, getting started, payload development, ROS2 interface reference, network architecture, web control API, rosbridge guide, performance benchmarks, troubleshooting, compliance checklist, SLAM alternatives, secrets management, fleet OTA strategy, fleet telemetry, Hailo integration, production deployment, competitive analysis, architecture diagrams
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
