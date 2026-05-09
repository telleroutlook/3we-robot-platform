<div align="center">

# Robot Platform

**Universal Modular Mobile Platform**

[![License](https://img.shields.io/badge/Code-Apache_2.0-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/Hardware-CERN--OHL--P_v2-green.svg)](LICENSE-HARDWARE)
[![License](https://img.shields.io/badge/Docs-CC_BY--SA_4.0-orange.svg)](LICENSE-DOCS)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%20|%20Jazzy-blueviolet.svg)](https://ros.org/)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.x-red.svg)](https://github.com/espressif/esp-idf)

An open-source omnidirectional mobile robot platform designed for<br/>
**modularity**, **extensibility**, and **rapid payload integration**.

<img src="docs/images/robot-platform-hero.png" alt="Robot Platform" width="600"/>

[Getting Started](#-quick-start) &bull;
[Documentation](docs/) &bull;
[Contributing](CONTRIBUTING.md) &bull;
[Hardware](hardware/)

**[English](README.md) | [中文](README_zh.md)**

</div>

---

> [!NOTE]
> This project is under active development. Hardware designs and firmware are being validated.

<br/>

## ✦ Core Capabilities

<table>
<tr>
<td width="50%">

**Motion & Control**
- Omnidirectional mecanum drive
- Closed-loop PID with encoder feedback
- 50 Hz control loop, < 20 ms latency
- Configurable speed limit (max 1.2 m/s)

</td>
<td width="50%">

**Intelligence & Navigation**
- Edge AI inference (Hailo-8/8L)
- Nav2 autonomous navigation
- SLAM with slam_toolbox
- ROS2 native integration

</td>
</tr>
<tr>
<td>

**Safety & Security**
- ISO 13850 hardware E-stop
- Dual-channel safety relay with self-test
- DTLS 1.2 encrypted communication
- Ed25519 signed OTA updates

</td>
<td>

**Modularity & Extensibility**
- PBC-34 hot-plug payload bus
- EEPROM auto-identification
- Power sequencing & budget management
- Multi-protocol: Wi-Fi / BLE / 4G / 5G / LoRa

</td>
</tr>
</table>

<br/>

## ✦ Product Line

| | **Basic** | **Standard** | **Pro** | **Industrial** |
|:--|:--:|:--:|:--:|:--:|
| **Target** | Education | Research | Commercial | Industrial |
| **AI** | — | Hailo-8L (13 TOPS) | Hailo-8 (26 TOPS) | Hailo-8 (26 TOPS) |
| **Connectivity** | Wi-Fi + BLE | Wi-Fi + BLE | + 4G | + 5G + LoRa |
| **CAN Bus** | — | — | — | MCP2515 + TJA1050 |
| **Protection** | IP20 | IP20 | IP40 | IP65 |

<br/>

## ✦ Architecture

```
┌───────────────────────────────────────────────────────────┐
│                       Payload Layer                         │
│            User devices via PBC-34 connector               │
├───────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│          ROS2  ·  Nav2  ·  SLAM  ·  Custom Nodes          │
├───────────────────────────────────────────────────────────┤
│                     Compute Layer                           │
│          Raspberry Pi 5  +  AI Accelerator (Hailo)         │
├───────────────────────────────────────────────────────────┤
│                     Firmware Layer                          │
│     ESP32-S3  ·  Motor  ·  Sensors  ·  Safety  ·  Comm    │
├───────────────────────────────────────────────────────────┤
│                     Hardware Layer                          │
│   Mecanum Wheels  ·  DRV8833  ·  Battery  ·  E-Stop       │
└───────────────────────────────────────────────────────────┘
```

<br/>

## ✦ Repository Structure

```
robot-platform/
│
├── firmware/                    # ESP32-S3 firmware (ESP-IDF + micro-ROS)
│   ├── esp32/main/             #   Application source
│   └── config/                 #   Pin definitions, robot parameters
│
├── ros2_ws/                    # ROS2 workspace
│   ├── robot_bringup/          #   Launch files, Nav2/SLAM config
│   ├── robot_description/      #   URDF model (Xacro)
│   └── robot_interfaces/       #   Custom msg/srv definitions
│
├── hardware/                   # Hardware design
│   ├── pcb/                    #   PCB specs, PBC-34 pinout
│   ├── structure/              #   Mechanical drawings
│   └── bom/                    #   Bill of materials (4 SKUs)
│
├── sdk/                        # Payload developer toolkit
│   ├── payload_interface/      #   Python communication library
│   ├── tools/                  #   EEPROM validator, diagnostics
│   ├── examples/               #   Reference implementations
│   └── web_basic/              #   Browser-based teleop UI
│
└── docs/                       # Documentation
    ├── assembly_guide.md       #   Hardware assembly
    ├── firmware_flash.md       #   Build & flash guide
    ├── payload_dev_guide.md    #   Payload development tutorial
    ├── compliance_checklist.md #   Regulatory compliance
    └── performance_benchmarks.md
```

<br/>

## ✦ Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/) | v5.x | Firmware build toolchain |
| [ROS2](https://docs.ros.org/en/humble/Installation.html) | Humble / Jazzy | Robot middleware |
| Python | 3.10+ | SDK and tools |
| [KiCad](https://www.kicad.org/) | 8+ | Hardware modifications (optional) |

### 1. Build & Flash Firmware

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

### 3. Launch the Robot

```bash
ros2 launch robot_bringup robot.launch.py
```

<br/>

## ✦ Tech Stack

| Layer | Technology | Role |
|:------|:-----------|:-----|
| MCU | ESP32-S3 | Dual-core 240 MHz, Wi-Fi + BLE |
| SBC | Raspberry Pi 5 (8 GB) | ROS2, navigation, vision |
| AI | Hailo-8L / Hailo-8 | 13–26 TOPS edge inference |
| RTOS | FreeRTOS (ESP-IDF) | Real-time motor + sensor control |
| Middleware | micro-ROS ↔ ROS2 | MCU–SBC bridge |
| Navigation | Nav2 + slam_toolbox | SLAM and path planning |
| Motor Driver | DRV8833 x2 | 4 × DC motor H-bridge |
| Security | DTLS 1.2 + Ed25519 OTA | Encrypted control, signed updates |
| Safety | ISO 13850 E-stop | Hardware interlock |

<br/>

## ✦ Licensing

This project uses an **Open Core** multi-license structure:

| Component | License | File |
|:----------|:--------|:-----|
| Firmware & Software | Apache License 2.0 | [`LICENSE`](LICENSE) |
| Hardware Designs | CERN-OHL-P v2 | [`LICENSE-HARDWARE`](LICENSE-HARDWARE) |
| Documentation | CC BY-SA 4.0 | [`LICENSE-DOCS`](LICENSE-DOCS) |

Third-party attributions: [`NOTICE`](NOTICE)

<br/>

## ✦ Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:

- Development environment setup
- Branch strategy & conventional commits
- Pull request process
- Safety-critical contribution rules

<br/>

## ✦ Safety Notice

> [!WARNING]
> This platform contains **moving mechanical parts** and **lithium batteries**.

- Always verify E-stop function before operation
- Never bypass or modify the safety relay circuit
- Follow battery handling guidelines in documentation
- Keep clear of wheel assemblies during operation

<br/>

## ✦ Community & Support

| Channel | Purpose |
|---------|---------|
| [GitHub Issues](../../issues) | Bug reports, feature requests |
| [GitHub Discussions](../../discussions) | Questions, ideas, show & tell |

<br/>

## ✦ Acknowledgments

Built on the shoulders of:

| Project | Maintainer |
|---------|-----------|
| [ESP-IDF](https://github.com/espressif/esp-idf) | Espressif Systems |
| [micro-ROS](https://micro.ros.org/) | eProsima |
| [ROS 2](https://ros.org/) | Open Robotics |
| [Nav2](https://nav2.org/) | Steve Macenski et al. |
| [KiCad](https://www.kicad.org/) | KiCad Community |

---

<div align="center">
<sub>Made with care for the robotics community.</sub>
</div>
