<div align="center">

# 3WE Robot Platform

**AI-First Open Infrastructure for Embodied Robotics**

[![License](https://img.shields.io/badge/Code-Apache_2.0-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/Hardware-CERN--OHL--P_v2-green.svg)](LICENSE-HARDWARE)
[![PyPI](https://img.shields.io/badge/pip_install-threewe-orange.svg)](sdk/threewe/)
[![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blueviolet.svg)](https://ros.org/)

The **open-source PyTorch for Embodied AI** — a complete robot platform
where the same 5 lines of Python run identically in simulation and on real hardware.

</div>

---

## 5 Lines to a Moving Robot

```python
from threewe import Robot

async with Robot(backend="gazebo") as robot:
    image = robot.get_image()
    await robot.move_to(x=2.0, y=1.0)
    pose = robot.get_pose()
```

Switch `backend="gazebo"` to `backend="real"` — zero code changes, same API.

---

## Why 3we?

| If you are... | 3we gives you... | Start here |
|:---|:---|:---|
| **AI/ML Researcher** | Gymnasium envs, VLM/VLA integration, trajectory recording — focus on your model, not ROS2 | [Getting Started (AI)](docs/getting_started_ai.md) |
| **Robotics Student** | Full stack from PCB to Python, <$500 hardware, production-grade code instead of toy examples | [Getting Started (Basic)](docs/getting_started_basic.md) |
| **RL Practitioner** | `gymnasium.make("3we/Navigation-v1")` — standard RL interface with real Sim2Real transfer | [Getting Started (AI)](docs/getting_started_ai.md) |
| **Hardware Builder** | Open BOM, assembly guide, CERN-OHL-P licensed PCB + structure | [Assembly Guide](docs/assembly_guide.md) |

---

## Quick Start

```bash
pip install threewe[sim]
```

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        # Navigate
        result = await robot.move_to(x=2.0, y=1.0)
        print(f"Reached: {result.success}")

        # VLM-powered instruction (requires: pip install threewe[ai])
        result = await robot.execute_instruction("go to the red door")

        # Get sensor data
        scan = robot.get_lidar_scan()
        imu = robot.get_imu()

asyncio.run(main())
```

### RL Training

```python
import gymnasium
import threewe.gym  # registers environments

env = gymnasium.make("3we/Navigation-v1")
obs, info = env.reset()

for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

### Benchmarks

```bash
threewe benchmark run --task pointnav --episodes 100 --backend gazebo
```

See the [Benchmark Leaderboard](docs/leaderboard.md) for baseline results and submission instructions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Your Python Code                            │
│  robot.move_to() · robot.get_image() · robot.execute_instruction│
├─────────────────────────────────────────────────────────────────┤
│                     threewe Python API                           │
│  Robot · Types · Config · AI (VLM/VLA) · Gym · Data · Benchmark │
├──────────────────┬──────────────────┬───────────────────────────┤
│  GazeboBackend   │   RealBackend    │   IsaacSimBackend (P2)    │
│  (Gazebo Harmonic│   (ROS2 Topics)  │   (Future)               │
│   + ros_gz_bridge│                  │                           │
├──────────────────┴──────────────────┴───────────────────────────┤
│                     ROS2 Jazzy + Nav2                            │
│   /cmd_vel · /scan · /odom · /camera · NavigateToPose Action    │
├─────────────────────────────────────────────────────────────────┤
│                     Firmware (ESP32-S3)                          │
│   Motor PID · Encoders · IMU · Safety Relay · micro-ROS         │
├─────────────────────────────────────────────────────────────────┤
│                     Hardware Layer                               │
│   Mecanum · DRV8833 · LD06 LiDAR · BNO055 · Battery · E-Stop   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Platform Comparison

| Feature | **3we** | TurtleBot 4 | LeRobot | Isaac Lab |
|:--------|:---:|:---:|:---:|:---:|
| Python API (no ROS2 knowledge) | **Yes** | No | N/A | Partial |
| Sim2Real (zero code change) | **Yes** | No | No | Yes |
| Open Hardware (PCB + BOM) | **Full** | Partial | N/A | N/A |
| Gymnasium Interface | **Yes** | No | Partial | Yes |
| VLM/VLA Integration | **Built-in** | No | Yes | No |
| Hardware Cost | **<$500** | ~$1200 | ~$2000+ | N/A |
| Payload Hot-plug Bus | **PBC-34** | USB | N/A | N/A |
| Safety (HW E-stop) | **ISO 13850** | Software | N/A | N/A |
| Encrypted Comms | **DTLS 1.2** | None | N/A | N/A |

---

## Hardware Specs

| Spec | Standard v2 |
|:-----|:---|
| Drive | 4-wheel Mecanum (65mm), omnidirectional |
| MCU | ESP32-S3 (dual-core 240MHz) |
| SBC | Raspberry Pi 5 (8GB) |
| AI Accelerator | Hailo-8L (13 TOPS) |
| LiDAR | LD06 (360°, 12m range) |
| IMU | BNO055 (9-axis fused) |
| Max Velocity | 0.5 m/s linear, 1.0 rad/s angular |
| Battery | 7.4V Li-ion, ~2h runtime |
| Safety | ISO 13850 E-stop + dual-channel relay |
| Connectivity | Wi-Fi + BLE (+ 4G/5G optional) |
| Reproduction Cost | <$500 |

---

## Repository Structure

```
3we-robot-platform/
├── sdk/threewe/          # AI-First Python package (pip install threewe)
│   ├── src/threewe/      #   Robot, Types, Backends, Gym, AI, Data, Benchmark
│   └── tests/            #   76+ unit tests
├── examples/             # Ready-to-run demo scripts
├── firmware/             # ESP32-S3 firmware (ESP-IDF + micro-ROS)
├── ros2_ws/              # ROS2 packages (Nav2, SLAM, Gazebo, Perception)
├── hardware/             # Open hardware (KiCad PCB, BOM, mechanical)
├── sdk/payload_interface/# Payload communication library
├── sdk/web_control/      # TypeScript Web Components control panel
├── monitoring/           # Prometheus + Grafana observability
└── docs/                 # Guides, API reference, tutorials
```

---

## Installation Options

```bash
# Core (types, Robot class, config)
pip install threewe

# With simulation (adds gymnasium)
pip install threewe[sim]

# With AI integration (adds openai, Pillow)
pip install threewe[ai]

# With data recording (adds h5py)
pip install threewe[data]

# Everything
pip install threewe[all]
```

For the **real hardware** backend, you also need ROS2 Jazzy:
```bash
# Ubuntu 24.04
sudo apt install ros-jazzy-desktop
```

---

## Examples

| Script | Description |
|:-------|:-----------|
| [`hello_world.py`](examples/hello_world.py) | Connect, capture image, navigate |
| [`vlm_navigation.py`](examples/vlm_navigation.py) | GPT-4o visual navigation |
| [`rl_obstacle_avoidance.py`](examples/rl_obstacle_avoidance.py) | PPO training in simulation |
| [`slam_exploration.py`](examples/slam_exploration.py) | Autonomous SLAM exploration |
| [`sim2real_demo.py`](examples/sim2real_demo.py) | Same code, different backends |
| [`data_collection.py`](examples/data_collection.py) | Record trajectories for imitation learning |

### Jupyter Notebooks

Step-by-step tutorials in [`notebooks/`](notebooks/):

| Notebook | Topic |
|:---------|:------|
| [01_hello_world](notebooks/01_hello_world.ipynb) | Connect, sensors, basic navigation |
| [02_slam_exploration](notebooks/02_slam_exploration.ipynb) | Autonomous mapping |
| [03_point_navigation](notebooks/03_point_navigation.ipynb) | Waypoints and path following |
| [04_rl_training](notebooks/04_rl_training.ipynb) | Gymnasium + PPO training |
| [05_data_collection](notebooks/05_data_collection.ipynb) | Record trajectories, export to LeRobot |

---

## Roadmap

- [x] **Phase 1**: ESP32 firmware + ROS2 stack + Hardware design
- [x] **Phase 1**: `threewe` Python API + Sim2Real backends
- [x] **Phase 1**: Gymnasium environments + VLM/VLA integration
- [x] **Phase 1**: Benchmark framework + Example scripts
- [ ] **Phase 2**: Isaac Sim backend
- [ ] **Phase 2**: Hardware Abstraction Layer for 3rd-party robots
- [ ] **Phase 2**: Foundation model fine-tuning pipelines
- [ ] **Phase 3**: 3we Hub (model/dataset sharing)
- [ ] **Phase 3**: Multi-robot fleet management

---

## Licensing

| Component | License | File |
|:----------|:--------|:-----|
| Firmware & Software | Apache License 2.0 | [`LICENSE`](LICENSE) |
| Hardware Designs | CERN-OHL-P v2 | [`LICENSE-HARDWARE`](LICENSE-HARDWARE) |
| Documentation | CC BY-SA 4.0 | [`LICENSE-DOCS`](LICENSE-DOCS) |

---

## Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development setup, branch strategy, and PR process.

---

## Safety Notice

> [!WARNING]
> This platform contains **moving mechanical parts** and **lithium batteries**.

- Always verify E-stop function before operation
- Never bypass or modify the safety relay circuit
- Follow battery handling guidelines in documentation
