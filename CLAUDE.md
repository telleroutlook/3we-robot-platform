# CLAUDE.md — Robot Platform Development Guide

## Project Overview

This is an open-source universal modular mobile platform. The architecture spans:

1. **Firmware** (ESP32-S3) — Motor control, sensor fusion, communication
2. **ROS2 Packages** — Navigation, SLAM, bringup, interfaces
3. **Hardware** — PCB design, mechanical structure, BOM
4. **SDK** — Payload interface library, examples, web basic tools
5. **Docs** — Assembly guides, API references, tutorials

The project follows an Open Core model: hardware, firmware, ROS2 stack, and SDK are fully open-source. Proprietary components (AI models, cloud services, advanced web panel) live in separate repositories.

## Architecture Principles

- **Modularity**: Each subsystem (locomotion, perception, communication, payload) is independently replaceable
- **Payload-first**: The platform exists to serve payloads — the standardized payload bus connector is the primary integration point
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
Scopes: `firmware`, `ros2`, `hardware`, `sdk`, `docs`

## Directory Responsibilities

```
firmware/       → ESP32 firmware source, build configs
  esp32/        → Main firmware application
  config/       → Shared configuration schemas
ros2_ws/        → ROS2 workspace (colcon packages)
  robot_bringup/     → Launch files, parameter configs
  robot_description/ → URDF/Xacro, meshes
  robot_diagnostics/ → Health monitoring, metrics exporter
  robot_interfaces/  → Custom msg/srv/action definitions
  robot_perception/  → Camera + AI inference (Hailo)
  robot_simulation/  → Gazebo simulation
hardware/       → Hardware design files
  pcb/          → KiCad projects (schematic + layout)
  structure/    → Mechanical CAD exports, drawings
  bom/          → Bill of materials
sdk/            → Payload developer toolkit
  payload_interface/ → Library for payload communication
  examples/     → Reference payload implementations
  tools/        → CLI tools (eeprom_validator, provision_keys)
  web_control/  → TypeScript Web Components (Lit-style)
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
# 1. Firmware — host-side unit tests (177 tests)
cd firmware/tests && make clean && make && ./test_runner

# 2. SDK web_control — TypeScript type-check
cd sdk/web_control && npx tsc --noEmit

# 3. SDK web_control — unit tests (41 tests, vitest)
cd sdk/web_control && npx vitest run

# 4. SDK web_control — Playwright E2E (53 tests)
cd sdk/web_control && npx playwright test

# 5. SDK web_control — lint & format
cd sdk/web_control && npx eslint src/ && npx prettier --check 'src/**/*.ts'

# 6. Python SDK — tests (118 tests, pytest)
cd sdk && python3 -m pytest tests/ -v

# 7. Python SDK — format and lint
ruff format --check sdk/ && ruff check sdk/

# 8. Cross-layer — ROS2 ↔ TypeScript ↔ firmware enum alignment
npx tsx scripts/validate-ros-types.ts
```

If any step fails, fix before committing.

### Test & Config Locations

| What | Location |
|------|----------|
| Firmware unit tests | `firmware/tests/` (Unity framework, Makefile) |
| Web unit tests | `sdk/web_control/src/**/*.test.ts` (Vitest, `vitest.config.ts`) |
| Web E2E tests | `sdk/web_control/tests/` (Playwright, `playwright.config.ts`) |
| Python SDK tests | `sdk/tests/` (pytest, config in `sdk/pyproject.toml`) |
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
- Specific GPIO pin assignments (see firmware config files)
- BOM pricing (see hardware/bom/)
- Certification status (see project management tools)
- Release schedule (see GitHub milestones)
- Contributor list (see git history)
- Detailed API docs (auto-generated from source)
