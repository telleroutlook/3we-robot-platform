# Changelog

All notable changes to the `threewe` Python package.

## [0.2.0] — 2026-05-13

First stable release of the AI-First Python API for embodied robotics research.

### Added

- **Robot class** — unified entry point with Gazebo, Isaac Sim, and Real hardware backends
- **Perception API** — `get_camera_image()`, `get_rgbd_image()`, `get_lidar_scan()`, `get_pose()`, `get_velocity()`, `get_imu()`, `get_battery_state()`, `get_map()`
- **Action API** — `set_velocity()`, `stop()`, `move_to()`, `move_forward()`, `rotate()`, `follow_path()`, `explore()`
- **AI Integration** — `execute_action()` for RL policies, `execute_instruction()` for VLM-powered navigation, `get_observation()` for standardized model input
- **Gymnasium environments** — `3we/Navigation-v1`, `3we/Exploration-v1`, `3we/ObjectNav-v1` with multi-agent support
- **VLA/VLM runners** — `VLARunner.from_pretrained()` for HuggingFace Hub models, Hailo-8L edge deployment support
- **Data recording** — `TrajectoryRecorder` with HDF5 export and LeRobot Hub format compatibility
- **Benchmark system** — PointNav, ObjectNav, Exploration tasks with standardized metrics (SPL, Success Rate, Coverage)
- **Scene registry** — 7 built-in scenes (office_v2, apartment_v1, corridor_v1, warehouse_v1, cluttered_v1, outdoor_v1, dynamic_v1)
- **HAL (Hardware Abstraction Layer)** — support for custom hardware profiles and third-party chassis
- **Domain randomization** — configurable sensor noise, physics parameters, and visual randomization
- **Sim2Real validation** — automated transfer ratio testing between backends
- **CLI** — `threewe launch`, `threewe benchmark run/compare/submit`, `threewe hal list`, `threewe test sim2real`
- **Experiment protocol** — standardized experiment configuration for reproducible research

### Infrastructure

- PyPI publishing via GitHub Actions (OIDC-based, on version tag push)
- 328 unit tests across all modules
- Python 3.10, 3.11, 3.12 support
- Ruff linting and formatting

## [0.2.0a2] — 2026-05-12

Pre-release alpha. All APIs present but under active development.

## [0.2.0a1] — 2026-05-10

Initial alpha with core Robot class and basic backends.
