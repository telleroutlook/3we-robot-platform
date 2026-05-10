# Integration Tests

Integration tests verify cross-layer communication and end-to-end behavior.

## Test Categories

| Category | Description | Requirements | Runs in CI? |
|----------|-------------|-------------|-------------|
| Simulation | Diagnostics, docking state machine | Gazebo headless | Yes |
| Cross-layer | Firmware ↔ ROS2 topic roundtrip | ESP32 + micro_ros_agent | No |
| End-to-end | Browser → WebSocket → ROS2 → motor | Full stack running | No |
| Hardware-in-loop | Physical sensor validation | Robot powered on | No |

## CI Simulation Tests

These tests run automatically in GitHub Actions using Gazebo in headless mode:

```bash
# Reproduce locally:
export QT_QPA_PLATFORM=offscreen
source /opt/ros/humble/setup.bash
source ros2_ws/install/setup.bash
ros2 launch robot_simulation gazebo.launch.py headless:=true &
sleep 10
pytest tests/integration/ -m "simulation and not hardware and not fullstack" --timeout=120 -v
```

Current CI simulation tests:
- `test_diagnostics_node.py` — Diagnostics node publishes, reports battery state, reports E-stop state
- Tests marked with `@pytest.mark.simulation`

### Headless Gazebo

The `headless:=true` argument launches Gazebo in server-only mode (`ign gazebo -s`), skipping the GUI. RViz2 is also suppressed. The `QT_QPA_PLATFORM=offscreen` environment variable prevents Qt from attempting X11 connections.

## Prerequisites (Hardware Tests)

- ROS2 Humble installed and sourced
- Workspace built: `cd ros2_ws && colcon build --symlink-install && source install/setup.bash`
- micro_ros_agent running: `ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 921600`
- Robot powered on with ESP32 connected via USB

## Hardware Validation Tests

Physical robot tests live in `tests/hardware_validation/scripts/`:

| Script | Purpose |
|--------|---------|
| `motor_sweep.py` | Ramps each motor through speed range, verifies encoder feedback |
| `encoder_calibrate.py` | Validates encoder tick count against known rotation |
| `ultrasonic_log.py` | Logs ultrasonic readings, checks for noise/outliers |

### Running Hardware Validation

```bash
python3 scripts/run-hardware-validation.py --subsystems motors encoders ultrasonic
```

This orchestrates all scripts with timeouts (60s each) and generates a JSON report.

### Running Specific Subsystems

```bash
python3 scripts/run-hardware-validation.py --subsystems motors
python3 scripts/run-hardware-validation.py --subsystems encoders
```

## Relationship to CI Tests

```
CI Tests (automated, fast, every PR)
├── Unit tests — function-level correctness
├── Config tests — YAML/URDF structure validation
├── E2E web tests — UI component behavior (mocked WebSocket)
└── Simulation tests — diagnostics, docking state machine (Gazebo headless)

Integration Tests (manual, requires hardware)
├── Hardware validation — sensor/actuator verification
├── Cross-layer — firmware ↔ ROS2 message flow
└── End-to-end — browser command → physical motion
```
