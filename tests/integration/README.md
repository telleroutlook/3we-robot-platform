# Integration Tests

Integration tests verify cross-layer communication and end-to-end behavior. Unlike unit tests (which run in CI), these require a physical robot or a full ROS2 simulation stack.

## Test Categories

| Category | Description | Requirements |
|----------|-------------|-------------|
| Cross-layer | Firmware ↔ ROS2 topic roundtrip | ESP32 + micro_ros_agent |
| End-to-end | Browser → WebSocket → ROS2 → motor | Full stack running |
| Hardware-in-loop | Physical sensor validation | Robot powered on |

## Prerequisites

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

## Future Integration Tests (Planned)

- [ ] E-stop activation → motor power cut verified via encoder silence
- [ ] Payload hot-plug sequence → PayloadState message published on `/payload/state`
- [ ] Nav2 goal → robot moves to target (simulation or physical)
- [ ] DTLS channel → cmd_vel delivered and executed
- [ ] OTA update → firmware version increments after flash
- [ ] Battery low → graceful shutdown sequence triggered

## Relationship to CI Tests

CI tests (`colcon test`, `pytest`, Playwright) validate code correctness without hardware. Integration tests validate physical behavior. Both are necessary; they serve different purposes:

```
CI Tests (automated, fast, every PR)
├── Unit tests — function-level correctness
├── Config tests — YAML/URDF structure validation
└── E2E web tests — UI component behavior (mocked WebSocket)

Integration Tests (manual, requires hardware)
├── Hardware validation — sensor/actuator verification
├── Cross-layer — firmware ↔ ROS2 message flow
└── End-to-end — browser command → physical motion
```
