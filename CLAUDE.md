# CLAUDE.md — Robot Platform Development Guide

## Project Overview

This is an AI-First open-source robot platform for Embodied AI research. The same Python code runs identically in simulation and on real hardware (Sim2Real with zero code changes). The architecture spans:

1. **Python SDK** (`threewe`) — AI-First API: Robot class, VLM/VLA integration, Gymnasium envs, trajectory recording, benchmarks
2. **Firmware** (ESP32-S3) — Motor control, sensor fusion, communication
3. **ROS2 Packages** — Navigation, SLAM, simulation backends (Gazebo, Isaac Sim)
4. **Hardware** — Open PCB design (CERN-OHL-P), mechanical structure, BOM (<$500 to reproduce)
5. **Docs** — AI getting started, assembly guides, API references

The project follows an Open Core model: hardware, firmware, ROS2 stack, and SDK are fully open-source. Proprietary components (AI models, cloud services, advanced web panel) live in separate repositories.

## Architecture Principles

- **Sim2Real consistency**: The Python API must behave identically across simulation and real hardware — zero code changes to switch backends
- **AI-First**: The primary interface is the `threewe` Python package; researchers should never need to touch ROS2 or firmware directly
- **Modularity**: Each subsystem (locomotion, perception, communication, payload) is independently replaceable
- **Safety by design**: Emergency stop and safety interlock are hardware-level, never software-only
- **Offline-capable**: Core functionality must work without network connectivity

## Development Environment

| Component | Toolchain |
|-----------|-----------|
| Firmware | ESP-IDF 5.x, micro-ROS |
| ROS2 | Humble or newer LTS |
| Python | 3.10+ |
| Hardware | KiCad 8+ |
| Docs | Markdown |

## Code Conventions

### License Headers

Every source file must begin with:

```
// SPDX-License-Identifier: Apache-2.0
```

For hardware files under CERN-OHL-P:
```
# SPDX-License-Identifier: CERN-OHL-P-2.0
```

### Naming

| Context | Convention | Example |
|---------|-----------|---------|
| C functions | snake_case with module prefix | `motor_set_speed()` |
| C defines | UPPER_SNAKE_CASE | `MAX_MOTOR_RPM` |
| ROS2 nodes | snake_case | `base_controller` |
| ROS2 topics | snake_case with `/` namespace | `/robot/cmd_vel` |
| Python | PEP 8 | `calculate_odometry()` |
| KiCad symbols | PascalCase | `MotorDriver_DRV8833` |

### Commit Format

Conventional Commits: `type(scope): description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `hw`
Scopes: `firmware`, `ros2`, `hardware`, `sdk`, `web`, `docs`

## Directory Responsibilities

```
firmware/       → ESP32 firmware source, build configs
  esp32/        → Main firmware application
  config/       → Shared configuration schemas
ros2_ws/        → ROS2 workspace (colcon packages)
  robot_bringup/     → Launch files, parameter configs
  robot_collection/  → Autonomous ball collection demo (state machine)
  robot_competition/ → RoboCup Logistics League competition nodes
  robot_description/ → URDF/Xacro, meshes
  robot_diagnostics/ → Health monitoring, metrics exporter
  robot_docking/     → Autonomous docking
  robot_interfaces/  → Custom msg/srv/action definitions
  robot_perception/  → Camera + AI inference (Hailo)
  robot_simulation/  → Gazebo simulation
hardware/       → Hardware design files
  pcb/          → KiCad projects (schematic + layout)
  structure/    → Mechanical CAD exports, drawings
  bom/          → Bill of materials
  charging_dock/ → Docking station hardware (PCB, BOM, docs)
  production/   → Manufacturing outputs (Gerbers, drill, positions)
  manufacturing/ → Manufacturing documentation
  validation/   → Hardware validation tests
sdk/            → Python SDK + Payload toolkit
  threewe/      → AI-First Python package (Robot, Gym, Benchmark)
  payload_interface/ → Library for payload communication
  examples/     → Reference payload implementations
  tools/        → CLI tools (eeprom_validator, provision_keys)
  web_control/  → TypeScript Web Components (vanilla, Shadow DOM)
  web_basic/    → Minimal zero-dependency teleop page
monitoring/     → Prometheus + Grafana observability stack
scripts/        → Automation (setup, validate, release)
tests/          → Integration and hardware validation tests
docs/           → User-facing documentation
```

## Safety Rules (Non-Negotiable)

These constraints must never be violated regardless of feature requirements:

1. **Emergency stop** — The physical E-stop must cut motor power through hardware relay. Software cannot override or bypass this path.
2. **Safety relay interlock** — Motor driver power must pass through the safety relay. No alternative power path is permitted.
3. **Payload isolation** — Payload code runs in a sandboxed context. It cannot directly access motor control, safety circuits, or core system configuration.
4. **OTA integrity** — Firmware updates must be cryptographically signed. Unsigned images must be rejected at the bootloader level.
5. **Communication encryption** — Control commands transmitted over wireless links must be encrypted (DTLS 1.2 or equivalent).

## Build & Test

### Firmware

```bash
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

### ROS2

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_bringup robot.launch.py
```

### Testing

- Firmware: Unity test framework, host-side build via gcc Makefile
- ROS2: `colcon test` with pytest and gtest
- SDK: pytest for Python, browser testing for web components

## Validation Checklist

Run these checks (in order) to verify cross-layer consistency after any code change.
Quick alias: `make all` runs lint + test + build from root.

```bash
# 1. Firmware — host-side unit tests
cd firmware/tests && make clean && make && ./test_runner

# 2. SDK web_control — TypeScript type-check
cd sdk/web_control && npx tsc --noEmit

# 3. SDK web_control — unit tests (vitest)
cd sdk/web_control && npx vitest run

# 4. SDK web_control — Playwright E2E
cd sdk/web_control && npx playwright test

# 5. SDK web_control — lint & format
cd sdk/web_control && npx eslint src/ && npx prettier --check 'src/**/*.ts'

# 6. Python SDK — tests (pytest)
cd sdk/threewe && PYTHONPATH=src:$PYTHONPATH python3 -m pytest tests/ -v

# 7. Python SDK — format and lint
ruff format --check sdk/ && ruff check sdk/

# 8. Cross-layer — ROS2 ↔ TypeScript ↔ firmware enum alignment
npx tsx scripts/validate-ros-types.ts

# 9. Cross-layer — firmware params ↔ ROS2 launch file
npx tsx scripts/validate-robot-params.ts

# 10. Cross-layer — GPIO pin conflicts, BOM alignment, Kconfig constraints
python3 scripts/validate-pin-conflicts.py
python3 scripts/validate-bom-firmware.py
python3 scripts/validate-kconfig-constraints.py
```

If any step fails, fix before committing.

### Test & Config Locations

| What | Location |
|------|----------|
| Firmware unit tests | `firmware/tests/` (Unity framework, Makefile) |
| Web unit tests | `sdk/web_control/src/**/*.test.ts` (Vitest, `vitest.config.ts`) |
| Web E2E tests | `sdk/web_control/tests/` (Playwright, `playwright.config.ts`) |
| Python SDK tests (threewe) | `sdk/threewe/tests/` (pytest, config in `sdk/threewe/pyproject.toml`) |
| Python SDK tests (payload) | `sdk/tests/` (pytest, config in `sdk/pyproject.toml`) |
| Integration tests | `tests/integration/` (pytest, `tests/integration/pytest.ini`) |
| ESLint config | `sdk/web_control/eslint.config.js` |
| Prettier config | `sdk/web_control/.prettierrc` |
| Coverage CI | `.github/workflows/coverage-report.yml` |
| Full CI | `.github/workflows/full-validation.yml` |
| Monitoring | `monitoring/` (Prometheus, Grafana, metrics exporter) |
| Env validation | `sdk/web_control/src/env.ts` + `sdk/payload_interface/env_validation.py` |

**Important**: Fix ALL errors and warnings — including pre-existing ones not caused by your current changes. Do not leave known issues unfixed or skip them because "they were already there." The codebase must be clean after every session.

## What NOT to Put Here

This file intentionally omits volatile information:
- Test counts (run the commands to get current numbers)
- Specific GPIO pin assignments (see firmware config files)
- BOM pricing (see hardware/bom/)
- Certification status (see project management tools)
- Release schedule (see GitHub milestones)
- Contributor list (see git history)
- Detailed API docs (auto-generated from source)
