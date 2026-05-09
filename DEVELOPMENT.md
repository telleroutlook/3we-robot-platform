# Development Guide

This guide helps you set up a development environment and contribute to the robot platform.

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Python | 3.10+ | SDK, hardware validation, tools |
| Node.js | 18+ | Web control UI, cross-layer validation |
| ESP-IDF | 5.x | Firmware compilation and flashing |
| ROS2 | Humble | Robot middleware, navigation |
| GCC | 12+ | Firmware unit tests (host build) |
| KiCad | 8+ | PCB design (optional) |

## Quick Start

```bash
# One-command setup (installs Python SDK, web deps, Playwright, runs checks)
./scripts/setup-dev-env.sh

# Skip firmware/ROS2 checks if you only work on SDK or web:
./scripts/setup-dev-env.sh --skip-firmware --skip-ros2
```

## Per-Subsystem Workflow

### Firmware (ESP32-S3)

```bash
# Source ESP-IDF environment
. $HOME/esp/esp-idf/export.sh

# Build (default SKU: standard)
cd firmware/esp32
idf.py set-target esp32s3
idf.py build

# Flash and monitor
idf.py -p /dev/ttyUSB0 flash monitor

# Build specific SKU variant
cp ../config/sdkconfig.defaults.pro sdkconfig.defaults
idf.py fullclean && idf.py build

# Run unit tests on host (no hardware needed)
cd firmware/tests
make clean && make
./test_runner
```

Available SKU variants: `basic`, `standard`, `pro`, `industrial`

### ROS2 Packages

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# Build all packages
cd ros2_ws
colcon build --symlink-install

# Source workspace overlay
source install/setup.bash

# Launch the full robot stack
ros2 launch robot_bringup bringup.launch.py

# Launch simulation
ros2 launch robot_simulation gazebo.launch.py
```

### Python SDK

```bash
# Install in editable mode with dev dependencies
pip install -e "sdk/[dev]"

# Run tests
pytest sdk/tests/ -v

# Lint and format
ruff check sdk/
ruff format sdk/
```

### Web Control UI

```bash
cd sdk/web_control

# Install dependencies
npm ci

# Start development server
npm run dev

# Type check
npx tsc --noEmit

# Run E2E tests
npx playwright test

# Production build
npm run build
```

## Validation Checklist

Before committing, run the full validation suite. These are the same checks CI runs:

```bash
# 1. Firmware host-side unit tests
cd firmware/tests && make clean && make && ./test_runner

# 2. TypeScript type check
cd sdk/web_control && npx tsc --noEmit

# 3. Playwright E2E tests
cd sdk/web_control && npx playwright test

# 4. Cross-layer type alignment (ROS2 ↔ TypeScript ↔ firmware)
npx tsx scripts/validate-ros-types.ts

# 5. Python lint and format
ruff format --check sdk/
ruff check sdk/

# 6. Python SDK tests
pytest sdk/tests/
```

If any step fails, fix before committing. Step 4 catches interface drift between ROS2 message definitions, TypeScript types, and firmware enums.

## Project Structure

```
firmware/           → ESP32-S3 firmware (C, ESP-IDF)
  esp32/main/       → Application source (motor, safety, comms, sensors)
  config/           → Shared params (robot_params.h, pin_definitions.h)
  tests/            → Host-side unit tests (Unity framework)
ros2_ws/            → ROS2 workspace
  robot_bringup/    → Launch files, QoS config, parameters
  robot_description/ → URDF/Xacro model
  robot_interfaces/ → Custom msg/srv definitions
  robot_simulation/ → Gazebo simulation
hardware/           → Hardware design
  pcb/              → KiCad 8 project (4-layer PCB)
  structure/        → Mechanical DXF drawings
  bom/              → Bill of materials (per SKU)
  manufacturing/    → Gerber/drill generation scripts
sdk/                → Developer SDK
  payload_interface/ → Python library for PBC-34 payloads
  examples/         → Reference payload implementations
  tools/            → CLI tools (eeprom-validator)
  web_control/      → TypeScript Web Components (Lit-style)
  web_basic/        → Minimal zero-dependency teleop page
docs/               → User documentation
scripts/            → Automation (setup, flash, validate, release)
tests/              → Hardware validation test plan and scripts
```

## Debugging Tips

### Firmware Serial Monitor

```bash
idf.py -p /dev/ttyUSB0 monitor

# Filter specific component logs
idf.py monitor --filter "safety"
idf.py monitor --filter "uros"
```

### ROS2 Diagnostics

```bash
# List active topics
ros2 topic list

# Monitor topic rate
ros2 topic hz /odom

# Echo messages
ros2 topic echo /battery_state

# Check node info
ros2 node info /robot_base

# System health
ros2 doctor
```

### Web Control UI

- Open browser DevTools → Network tab to verify WebSocket connection to rosbridge
- The `RosbridgeConnection` emits `statechange` events — listen for `error` state
- Default rosbridge URL: `ws://localhost:9090`

### micro-ROS Agent

```bash
# Start agent on host (matches firmware's serial transport)
ros2 run micro_ros_agent micro_ros_agent serial \
    --dev /dev/ttyUSB0 --baudrate 921600

# Or UDP transport (if configured in firmware)
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888
```

## IDE Setup

### VS Code (Recommended)

Extensions:
- **ESP-IDF** — Build, flash, monitor from VS Code
- **C/C++** — IntelliSense for firmware code
- **ROS** — ROS2 launch, topic, service integration
- **Lit Plugin** — Web component development
- **ESLint** + **Prettier** — TypeScript formatting

Workspace settings (`.vscode/settings.json`):
```json
{
  "C_Cpp.default.compilerPath": "${env:IDF_PATH}/../tools/xtensa-esp32s3-elf/*/bin/xtensa-esp32s3-elf-gcc",
  "C_Cpp.default.includePath": [
    "${workspaceFolder}/firmware/esp32/main/**",
    "${workspaceFolder}/firmware/config/**"
  ],
  "python.defaultInterpreterPath": ".venv/bin/python"
}
```

## Commit Convention

```
type(scope): description

feat(firmware): add BLE provisioning mode
fix(sdk): correct CRC calculation for 0-length payloads
docs(ros2): add topic reference table
test(web): add E2E test for estop button
hw(pcb): update decoupling capacitor footprint
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `hw`
Scopes: `firmware`, `ros2`, `hardware`, `sdk`, `docs`, `web`

## Hardware-in-the-Loop Testing

For physical robot testing, see the [Hardware Validation Test Plan](tests/hardware_validation/README.md).

```bash
# Run the automated hardware validation suite
python3 scripts/run-hardware-validation.py

# Run individual subsystem
python3 scripts/run-hardware-validation.py --subsystem motors
```

These tests require a physical robot with ROS2 running. They are never executed in CI.
