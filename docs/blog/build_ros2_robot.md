# Build a 2200 RMB ($300) ROS2 Research Robot from Scratch

A complete ROS2 research robot with mecanum omnidirectional drive, 2D LiDAR SLAM, edge AI inference, and a Python API that lets you write your first autonomous behavior in 10 lines of code. Total hardware cost: under 2200 RMB (~$300 USD). No custom PCBs required for the first prototype -- everything is off-the-shelf from Taobao or AliExpress.

For context, a TurtleBot4 Lite costs $1,200+. A custom university research platform typically runs $2,000-5,000 by the time you source sensors, compute, and a chassis. The 3we platform achieves comparable sensing and compute capability at a fraction of the cost, with the added advantage of a Python-first SDK that eliminates the ROS2 learning curve.

---

## Hardware Overview

| Component | Part | Approx. Cost (RMB) |
|-----------|------|---------------------|
| Compute | Raspberry Pi 5 (8GB) + Hailo-8L AI Hat | 650 |
| Microcontroller | ESP32-S3 DevKitC-1 | 35 |
| LiDAR | LD06 360-degree 2D LiDAR | 100 |
| IMU | BNO055 9-DOF IMU | 45 |
| Camera | 160-degree Fisheye USB Camera (1080p) | 80 |
| Motors | 4x JGA25-370 DC Motors with Encoders | 120 |
| Motor Driver | 2x DRV8833 Dual H-Bridge | 20 |
| Wheels | 4x 65mm Mecanum Wheels | 160 |
| Battery | 3S 2200mAh LiPo + BMS | 120 |
| Chassis | 200x200mm Aluminum Plate + Standoffs | 80 |
| Power | 5V/5A Buck Converter (for Pi5) | 25 |
| Safety | Emergency Stop Button + Relay | 30 |
| Wiring | Connectors, cables, crimps | 50 |
| Fasteners | M3/M4 bolts, nuts, spacers | 30 |
| **Total** | | **~1545 RMB (~$215)** |

With the optional upgrades below, the full research configuration reaches ~2200 RMB:

| Optional Upgrade | Part | Cost (RMB) |
|-----------------|------|-------------|
| Depth sensing | Intel RealSense D405 (used) | 350 |
| Better compute | Pi 5 (16GB) instead of 8GB | +100 |
| Charging dock | Custom dock PCB + contacts | 200 |
| **Total with upgrades** | | **~2200 RMB (~$300)** |

---

## Why These Specific Parts

### Raspberry Pi 5 + Hailo-8L

The Pi 5 runs ROS2 Jazzy natively at 1.5x the performance of Pi 4. The Hailo-8L AI accelerator (13 TOPS) plugs in via M.2 hat and runs YOLO, MobileNet, and custom VLA models at 30+ FPS without touching the CPU. This combination gives you:

- Full ROS2 stack (Nav2, SLAM, perception)
- 13 TOPS neural inference for on-device AI
- USB3 for cameras, Ethernet for remote development
- Under 8W total system power

### ESP32-S3 for Motor Control

The ESP32-S3 handles real-time motor control via micro-ROS, communicating with the Pi over USB-CDC at 1000Hz. It runs:

- PID velocity control for all 4 motors
- Encoder counting (4 channels, quadrature)
- IMU fusion at 100Hz
- Safety watchdog (stops motors if communication drops)

This architecture separates hard real-time (motor control) from soft real-time (navigation, perception), which is critical for reliable robot operation.

### LD06 LiDAR

The LD06 is a $14 360-degree 2D LiDAR with 12m range and 4500 samples/sec. It interfaces via UART and works directly with the ROS2 `ldlidar` package. For SLAM and obstacle avoidance in indoor environments, it performs comparably to LiDARs costing 10x more.

### Mecanum Wheels

Mecanum wheels give the platform omnidirectional movement (forward, sideways, diagonal, rotation in place) without a complex steering mechanism. This is essential for:

- Tight indoor navigation (corridors, under desks)
- Precise docking maneuvers
- Holonomic motion planning (simplifies Nav2 configuration)

---

## Software Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Your Python Code                        │
│    from threewe import Robot                              │
│    await robot.move_to(x=2.0, y=1.5)                    │
├─────────────────────────────────────────────────────────┤
│                  threewe Python SDK                       │
│  Robot, VLMRunner, VLARunner, Gymnasium Envs             │
├─────────────────────────────────────────────────────────┤
│              Backend Abstraction Layer                    │
│    GazeboBackend │ IsaacSimBackend │ RealBackend         │
├─────────────────────────────────────────────────────────┤
│                    ROS2 Jazzy                             │
│    Nav2 │ SLAM Toolbox │ robot_perception │ micro-ROS    │
├──────────────────────┬──────────────────────────────────┤
│   Raspberry Pi 5     │        ESP32-S3                   │
│   + Hailo-8L         │   Motor PID + Encoders            │
│   Camera, LiDAR      │   IMU, Safety Watchdog            │
└──────────────────────┴──────────────────────────────────┘
```

The key insight: **you never need to learn ROS2**. The `threewe` SDK exposes everything through Python:

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="real") as robot:
        # Get sensor data
        image = robot.get_camera_image()     # (480, 640, 3) uint8
        scan = robot.get_lidar_scan()        # 360 range measurements
        pose = robot.get_pose()              # x, y, theta in map frame

        # Navigate
        await robot.move_to(x=2.0, y=1.5)   # Uses Nav2 path planning
        await robot.move_forward(1.0)        # Drive 1 meter forward
        await robot.rotate(1.57)             # Rotate 90 degrees

        # AI inference (runs on Hailo-8L)
        result = await robot.execute_instruction("find the door")

asyncio.run(main())
```

Under the hood, `RealBackend` translates these calls to ROS2 service calls, action clients, and topic subscriptions. But you never see that complexity.

---

## Try Without Hardware First

You do not need to buy any hardware to start developing:

```bash
pip install threewe[sim]
threewe launch --backend gazebo --scene office_v2
```

This launches a Gazebo simulation with the 3we robot model in an office environment. Your Python code works identically:

```python
async with Robot(backend="gazebo") as robot:
    await robot.move_to(x=2.0, y=1.5)
    image = robot.get_camera_image()
```

When you are ready to move to hardware, change `backend="gazebo"` to `backend="real"`. That is the only modification needed.

---

## Assembly Overview

The full assembly guide is in `docs/assembly_guide.md`. Here are the key steps:

### 1. Chassis Assembly (30 minutes)

Cut or order the 200x200mm aluminum plate. Mount the 4 motors with L-brackets. Attach mecanum wheels (pay attention to the diagonal pattern -- wrong orientation breaks omnidirectional movement).

```
  ┌────────────────┐
  │  FL ╲    ╱ FR  │    FL/BR: Left-handed rollers
  │       ╲╱       │    FR/BL: Right-handed rollers
  │       ╱╲       │
  │  BL ╱    ╲ BR  │    Viewed from above
  └────────────────┘
```

### 2. Electronics Stack (45 minutes)

Mount components on standoffs in layers:

- Bottom: Battery + BMS + buck converter
- Middle: ESP32-S3 + motor drivers
- Top: Raspberry Pi 5 + Hailo-8L hat + LiDAR

### 3. Wiring (60 minutes)

Key connections:

| From | To | Interface |
|------|-----|-----------|
| Pi 5 | ESP32-S3 | USB-C (micro-ROS) |
| ESP32-S3 | DRV8833 x2 | GPIO (PWM + DIR) |
| DRV8833 | Motors | Direct wire |
| Pi 5 | LD06 LiDAR | USB-UART |
| Pi 5 | Camera | USB3 |
| ESP32-S3 | BNO055 | I2C |
| E-Stop | Safety Relay | NC contact |
| Safety Relay | Motor power | Inline |

### 4. Software Setup (20 minutes)

```bash
# On Raspberry Pi 5 (Ubuntu 24.04 with ROS2 Jazzy pre-installed)
git clone https://github.com/3we-org/3we-robot-platform.git
cd 3we-robot-platform

# Install ROS2 packages
cd ros2_ws && colcon build --symlink-install
source install/setup.bash

# Flash ESP32-S3 firmware
cd firmware/esp32
idf.py set-target esp32s3
idf.py build && idf.py flash

# Install Python SDK
pip install threewe

# Launch everything
ros2 launch robot_bringup robot.launch.py
```

### 5. First Test (5 minutes)

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="real") as robot:
        # Simple motion test
        await robot.move_forward(0.5)   # Move 50cm forward
        await robot.rotate(3.14)        # Turn around
        await robot.move_forward(0.5)   # Come back

asyncio.run(main())
```

---

## Comparison: 3we vs Alternatives

| Feature | 3we Platform | TurtleBot4 Lite | Custom Build |
|---------|-------------|-----------------|--------------|
| **Cost** | ~$300 | $1,200+ | $2,000-5,000 |
| **Drive type** | Mecanum (omnidirectional) | Differential | Varies |
| **Edge AI** | Hailo-8L (13 TOPS) | None standard | Add-on |
| **LiDAR** | LD06 (360-deg) | RPLiDAR (360-deg) | Varies |
| **Camera** | Fisheye 1080p | OAK-D Lite | Varies |
| **Python API** | threewe SDK | Custom | Custom |
| **Sim2Real** | Built-in (Gazebo/Isaac) | Separate setup | Manual |
| **SLAM** | SLAM Toolbox | SLAM Toolbox | Manual |
| **Navigation** | Nav2 (pre-configured) | Nav2 | Manual |
| **VLM/VLA support** | Built-in | None | Manual |
| **Gymnasium envs** | Included | None | Manual |
| **Open hardware** | Full (CERN-OHL-P) | Proprietary | Varies |
| **Reproducibility** | High (BOM, guides) | Buy pre-built | Low |
| **Time to first demo** | 2-3 hours | 30 min (pre-built) | Days-weeks |

The key differentiator is not any single spec -- it is the integrated experience. A Python researcher can go from `pip install threewe[sim]` to training RL agents and deploying on hardware without ever writing a ROS2 node, configuring Nav2, or debugging TF trees.

---

## Parts Sourcing

All components are available from mainstream Chinese electronics retailers and AliExpress for international buyers:

### Taobao (China)

| Part | Search Term | Typical Store |
|------|-------------|---------------|
| Pi 5 | "树莓派5 8GB" | Official Pi store |
| Hailo-8L | "Hailo-8L M.2 AI Hat" | Waveshare |
| ESP32-S3 | "ESP32-S3-DevKitC-1" | Espressif store |
| LD06 LiDAR | "LD06 激光雷达" | LDRobot store |
| BNO055 | "BNO055 九轴" | Various |
| JGA25-370 | "JGA25-370 编码器电机" | Various |
| Mecanum wheels | "65mm 麦克纳姆轮" | Various |
| DRV8833 | "DRV8833 电机驱动" | Various |

### AliExpress (International)

Search the English part names. Most ship worldwide in 2-3 weeks. The LD06 LiDAR and mecanum wheels are particularly easy to find.

### No Custom Parts Required

The first-generation platform uses zero custom PCBs. Everything connects with standard dupont wires, USB cables, and screw terminals. The custom charging dock PCB is optional and only needed for autonomous long-duration experiments.

---

## What You Can Do With It

### 1. Indoor Navigation Research

```python
async with Robot(backend="real") as robot:
    # SLAM is running automatically
    occupancy_map = robot.get_map()

    # Navigate to any reachable point
    result = await robot.move_to(x=5.0, y=3.0)
    print(f"Arrived: {result.success}, distance: {result.distance:.2f}m")
```

### 2. Object Navigation with VLM

```python
async with Robot(backend="real") as robot:
    result = await robot.execute_instruction(
        "go to the kitchen and find the coffee mug"
    )
```

### 3. RL Training in Simulation

```python
import gymnasium as gym
import threewe.gym  # Registers environments

env = gym.make("threewe/NavigationEnv-v0", render_mode="rgb_array")
obs, info = env.reset()

for _ in range(1000):
    action = your_policy(obs)
    obs, reward, terminated, truncated, info = env.step(action)
```

### 4. VLA Model Deployment

```python
from threewe.ai.vla_runner import VLARunner

vla = VLARunner.from_pretrained("lerobot/act_3we_nav")

async with Robot(backend="real") as robot:
    while True:
        obs = robot.get_observation(modalities=["image", "lidar", "velocity"])
        action = vla.predict(obs, instruction="patrol the office")
        robot.execute_action(action)
```

### 5. Benchmarking

```bash
# Run 100 episodes of point-goal navigation
threewe benchmark run --task pointnav --episodes 100 --backend gazebo

# Compare against baselines
threewe benchmark compare --result results.json --baseline random_walk

# Submit to community leaderboard
threewe benchmark submit --result results.json
```

### 6. Multi-Robot Experiments

The platform supports multiple robots in simulation. Each robot instance connects independently:

```python
async def multi_robot():
    async with Robot(backend="gazebo", config="robot_1") as r1:
        async with Robot(backend="gazebo", config="robot_2") as r2:
            # Coordinate two robots
            await asyncio.gather(
                r1.move_to(x=2.0, y=0.0),
                r2.move_to(x=-2.0, y=0.0),
            )
```

---

## Safety Design

The platform implements hardware-level safety that cannot be bypassed by software:

1. **Physical E-Stop**: A big red mushroom button that cuts motor power through a normally-closed relay. Pressing it immediately removes power from all motor drivers regardless of what the software is doing.

2. **Communication Watchdog**: The ESP32-S3 firmware has a 200ms watchdog. If it does not receive a velocity command for 200ms, motors stop automatically. This protects against Pi crashes, network drops, or hung processes.

3. **Velocity Limits**: Hard-coded in both firmware and SDK. Maximum linear velocity is 0.5 m/s, maximum angular velocity is 1.0 rad/s. These cannot be overridden without reflashing the firmware.

4. **Safety Distance**: The SDK enforces a 15cm safety buffer -- if LiDAR detects an obstacle within 15cm, motion commands are rejected with a `SafetyError`.

---

## Upgrading Over Time

The modular design means you can start minimal and upgrade incrementally:

| Stage | Hardware | Capability |
|-------|----------|------------|
| Stage 1 | Pi5 + ESP32 + Motors + LiDAR | Navigation, SLAM |
| Stage 2 | + Camera | Visual perception, VLM control |
| Stage 3 | + Hailo-8L | On-device AI, real-time detection |
| Stage 4 | + RealSense | 3D mapping, depth-based avoidance |
| Stage 5 | + Charging dock | Autonomous long-duration experiments |

Each stage requires no changes to existing code. The SDK detects available hardware and adapts.

---

## Quick Start Summary

```bash
# 1. Try in simulation first (no hardware needed)
pip install threewe[sim]
threewe launch --backend gazebo --scene office_v2

# 2. Write your first autonomous behavior
python -c "
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend='gazebo') as robot:
        await robot.move_to(x=2.0, y=1.5)
        print('Arrived!')

asyncio.run(main())
"

# 3. When ready, build hardware (see docs/assembly_guide.md)
# 4. Change backend="gazebo" to backend="real"
# 5. Run the same code on your physical robot
```

---

## Links

- GitHub: [https://github.com/3we-org/3we-robot-platform](https://github.com/3we-org/3we-robot-platform)
- Full BOM spreadsheet: `hardware/bom/`
- Assembly guide: `docs/assembly_guide.md`
- Hardware design files (KiCad): `hardware/pcb/`
- Mechanical drawings: `hardware/structure/`
- PyPI: [https://pypi.org/project/threewe](https://pypi.org/project/threewe)

---

Published by the 3we team
