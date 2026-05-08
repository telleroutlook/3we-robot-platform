# Robot Platform 🤖

**通用模块化移动平台 — Universal Modular Mobile Platform**

An open-source omnidirectional mobile robot platform designed for modularity, extensibility, and rapid payload integration.

> [!NOTE]
> This project is under active development. Hardware designs and firmware are being validated.

---

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| Omnidirectional Movement | Mecanum wheel drive with independent motor control |
| Onboard AI | Edge inference for vision, tracking, and navigation |
| Standardized Payload Bus | Hot-plug connector with auto-identification (EEPROM) |
| Multi-Protocol Communication | Wi-Fi, BLE, 4G/5G, LoRa (model dependent) |
| Hardware Safety | Physical E-stop + safety relay interlock (ISO 13850) |
| ROS2 Native | Full Nav2 + SLAM integration out of the box |

---

## Product Line

| SKU | Target Use Case | AI | Communication |
|-----|----------------|-----|---------------|
| Basic | Education, Hobby | — | Wi-Fi + BLE |
| Standard | Research, Prototyping | Hailo-8L | Wi-Fi + BLE |
| Pro | Commercial Deployment | Hailo-8 | Wi-Fi + BLE + 4G |
| Industrial | Industrial Automation | Hailo-8 | Wi-Fi + BLE + 5G + LoRa |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Payload Layer                    │
│         (User devices via PBC-34 connector)      │
├─────────────────────────────────────────────────┤
│              Application Layer                    │
│      ROS2 (Nav2, SLAM, Custom Nodes)            │
├─────────────────────────────────────────────────┤
│              Compute Layer                        │
│     Raspberry Pi 5 + AI Accelerator             │
├─────────────────────────────────────────────────┤
│              Firmware Layer                       │
│   ESP32-S3 (Motor, Sensors, Communication)      │
├─────────────────────────────────────────────────┤
│              Hardware Layer                       │
│  Mecanum Wheels, Drivers, Battery, Safety       │
└─────────────────────────────────────────────────┘
```

---

## Repository Structure

```
robot-platform/
├── firmware/          # ESP32-S3 firmware (ESP-IDF + micro-ROS)
│   ├── esp32/         # Main application
│   └── config/        # Configuration schemas
├── ros2_ws/           # ROS2 workspace
│   ├── robot_bringup/      # Launch files
│   ├── robot_description/  # URDF, meshes
│   └── robot_interfaces/   # Custom msg/srv/action
├── hardware/          # Hardware design
│   ├── pcb/           # KiCad projects
│   ├── structure/     # Mechanical drawings
│   └── bom/           # Bill of materials
├── sdk/               # Payload developer toolkit
│   ├── payload_interface/  # Communication library
│   ├── examples/      # Reference implementations
│   └── web_basic/     # Minimal web control UI
├── docs/              # Documentation
├── LICENSE            # Apache 2.0 (code)
├── LICENSE-HARDWARE   # CERN-OHL-P v2 (hardware)
└── LICENSE-DOCS       # CC BY-SA 4.0 (documentation)
```

---

## Quick Start

### Prerequisites

- ESP-IDF v5.x ([Installation Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/))
- ROS2 Humble or Jazzy ([Installation Guide](https://docs.ros.org/en/humble/Installation.html))
- Python 3.10+
- KiCad 8+ (for hardware modifications)

### 1. Build Firmware

```bash
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

### 2. Build ROS2 Workspace

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 3. Launch

```bash
ros2 launch robot_bringup bringup.launch.py
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| MCU | ESP32-S3 (dual-core, 240MHz, Wi-Fi + BLE) |
| SBC | Raspberry Pi 5 (8GB) |
| AI Accelerator | Hailo-8L / Hailo-8 (13/26 TOPS) |
| RTOS | FreeRTOS (via ESP-IDF) |
| Middleware | micro-ROS ↔ ROS2 |
| Navigation | Nav2 + slam_toolbox |
| Vision | ONNX Runtime + OpenCV |
| Motor Driver | DRV8833 (dual H-bridge) |
| Safety | ISO 13850 E-stop + dual-channel safety relay |

---

## Licensing

This project uses a multi-license structure:

| Component | License | File |
|-----------|---------|------|
| Firmware & Software | Apache License 2.0 | `LICENSE` |
| Hardware Designs | CERN-OHL-P v2 | `LICENSE-HARDWARE` |
| Documentation | CC BY-SA 4.0 | `LICENSE-DOCS` |

See `NOTICE` for third-party dependency attributions.

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Branch strategy and commit format
- Pull request process
- Code style guidelines
- Safety-critical contribution rules

---

## Safety Notice

This platform includes moving mechanical parts and lithium batteries. Please:

- Always verify the E-stop button functions before operation
- Do not bypass or modify the safety relay circuit
- Follow battery handling guidelines in the documentation
- Keep clear of wheel assemblies during operation

---

## Community

- [GitHub Issues](../../issues) — Bug reports and feature requests
- [GitHub Discussions](../../discussions) — Questions and ideas

---

## Roadmap

See [GitHub Milestones](../../milestones) for planned releases.

---

## Acknowledgments

Built with:
- [ESP-IDF](https://github.com/espressif/esp-idf) by Espressif
- [micro-ROS](https://micro.ros.org/) by eProsima
- [ROS 2](https://ros.org/) by Open Robotics
- [Nav2](https://nav2.org/) by Steve Macenski et al.
- [KiCad](https://www.kicad.org/) EDA

---

*Made with care for the robotics community.*
