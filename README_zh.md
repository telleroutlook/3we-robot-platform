<div align="center">

# 3WE Robot Platform

**AI-First 开源具身智能基础设施**

[![License](https://img.shields.io/badge/代码-Apache_2.0-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/硬件-CERN--OHL--P_v2-green.svg)](LICENSE-HARDWARE)
[![PyPI](https://img.shields.io/badge/pip_install-threewe-orange.svg)](sdk/threewe/)
[![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blueviolet.svg)](https://ros.org/)

**开源版"Embodied AI 的 PyTorch"** —— 一个完整的机器人平台，
同样 5 行 Python 在仿真和真机上零代码修改运行。

</div>

---

## 5 行代码驱动机器人

```python
from threewe import Robot

async with Robot(backend="gazebo") as robot:
    image = robot.get_image()
    await robot.move_to(x=2.0, y=1.0)
    pose = robot.get_pose()
```

将 `backend="gazebo"` 切换为 `backend="real"` —— 零代码修改，同一 API。

---

## 为什么选择 3we？

| 如果你是... | 3we 提供... | 入口 |
|:---|:---|:---|
| **AI/ML 研究者** | Gymnasium 环境、VLM/VLA 集成、轨迹录制 —— 专注模型，无需学 ROS2 | [快速开始 (AI)](docs/getting_started_ai.md) |
| **机器人学生** | 从 PCB 到 Python 的完整栈，硬件 <$500，生产级代码而非玩具示例 | [快速开始 (基础)](docs/getting_started_basic.md) |
| **RL 研究者** | `gymnasium.make("3we/Navigation-v1")` —— 标准 RL 接口，真正的 Sim2Real 迁移 | [快速开始 (AI)](docs/getting_started_ai.md) |
| **硬件爱好者** | 开放 BOM、组装指南、CERN-OHL-P 开源 PCB + 结构件 | [组装指南](docs/assembly_guide.md) |

---

## 快速开始

```bash
pip install threewe[sim]
```

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        # 导航
        result = await robot.move_to(x=2.0, y=1.0)
        print(f"到达: {result.success}")

        # VLM 视觉导航（需要: pip install threewe[ai]）
        result = await robot.execute_instruction("走到红色门旁边")

        # 传感器数据
        scan = robot.get_lidar_scan()
        imu = robot.get_imu()

asyncio.run(main())
```

### 强化学习训练

```python
import gymnasium
import threewe.gym  # 自动注册环境

env = gymnasium.make("3we/Navigation-v1")
obs, info = env.reset()

for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

### 基准测试

```bash
threewe benchmark run --task pointnav --episodes 100 --backend gazebo
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      你的 Python 代码                             │
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
│                     固件层 (ESP32-S3)                             │
│   电机 PID · 编码器 · IMU · 安全继电器 · micro-ROS              │
├─────────────────────────────────────────────────────────────────┤
│                     硬件层                                        │
│   麦克纳姆轮 · DRV8833 · LD06 LiDAR · BNO055 · 电池 · 急停     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 平台对比

| 特性 | **3we** | TurtleBot 4 | LeRobot | Isaac Lab |
|:--------|:---:|:---:|:---:|:---:|
| Python API（无需 ROS2 知识） | **是** | 否 | N/A | 部分 |
| Sim2Real（零代码修改） | **是** | 否 | 否 | 是 |
| 开放硬件（PCB + BOM） | **完全** | 部分 | N/A | N/A |
| Gymnasium 接口 | **是** | 否 | 部分 | 是 |
| VLM/VLA 集成 | **内置** | 否 | 是 | 否 |
| 硬件成本 | **<$500** | ~$1200 | ~$2000+ | N/A |
| 载荷热插拔总线 | **PBC-34** | USB | N/A | N/A |
| 硬件安全（急停） | **ISO 13850** | 仅软件 | N/A | N/A |
| 加密通信 | **DTLS 1.2** | 无 | N/A | N/A |

---

## 硬件规格

| 参数 | Standard v2 |
|:-----|:---|
| 驱动 | 四麦克纳姆轮（65mm），全向移动 |
| MCU | ESP32-S3（双核 240MHz） |
| SBC | Raspberry Pi 5（8GB） |
| AI 加速 | Hailo-8L（13 TOPS） |
| LiDAR | LD06（360°，12m 测距） |
| IMU | BNO055（九轴融合） |
| 最大速度 | 0.5 m/s 线速度，1.0 rad/s 角速度 |
| 电池 | 7.4V 锂电池，约 2h 续航 |
| 安全 | ISO 13850 急停 + 双通道继电器 |
| 通信 | Wi-Fi + BLE（+ 4G/5G 可选） |
| 复现成本 | <$500 |

---

## 仓库结构

```
3we-robot-platform/
├── sdk/threewe/          # AI-First Python 包 (pip install threewe)
│   ├── src/threewe/      #   Robot, Types, Backends, Gym, AI, Data, Benchmark
│   └── tests/            #   76+ 单元测试
├── examples/             # 开箱即用的示例脚本
├── firmware/             # ESP32-S3 固件 (ESP-IDF + micro-ROS)
├── ros2_ws/              # ROS2 包 (Nav2, SLAM, Gazebo, Perception)
├── hardware/             # 开源硬件 (KiCad PCB, BOM, 结构件)
├── sdk/payload_interface/# 载荷通信库
├── sdk/web_control/      # TypeScript Web 组件控制面板
├── monitoring/           # Prometheus + Grafana 可观测性
└── docs/                 # 教程、API 参考、指南
```

---

## 安装选项

```bash
# 核心（类型、Robot 类、配置）
pip install threewe

# 含仿真支持（增加 gymnasium）
pip install threewe[sim]

# 含 AI 集成（增加 openai, Pillow）
pip install threewe[ai]

# 含数据录制（增加 h5py）
pip install threewe[data]

# 全部
pip install threewe[all]
```

**真机**后端还需要 ROS2 Jazzy：
```bash
# Ubuntu 24.04
sudo apt install ros-jazzy-desktop
```

---

## 示例

| 脚本 | 说明 |
|:-------|:-----------|
| [`hello_world.py`](examples/hello_world.py) | 连接、采集图像、导航 |
| [`vlm_navigation.py`](examples/vlm_navigation.py) | GPT-4o 视觉导航 |
| [`rl_obstacle_avoidance.py`](examples/rl_obstacle_avoidance.py) | PPO 仿真训练 |
| [`slam_exploration.py`](examples/slam_exploration.py) | 自主 SLAM 探索 |
| [`sim2real_demo.py`](examples/sim2real_demo.py) | 同一代码，不同后端 |
| [`data_collection.py`](examples/data_collection.py) | 录制模仿学习轨迹 |

### Jupyter 教程

[`notebooks/`](notebooks/) 中的交互式教程：

| Notebook | 主题 |
|:---------|:------|
| [01_hello_world](notebooks/01_hello_world.ipynb) | 连接、传感器、基础导航 |
| [02_slam_exploration](notebooks/02_slam_exploration.ipynb) | 自主建图 |
| [03_point_navigation](notebooks/03_point_navigation.ipynb) | 航点与路径跟踪 |
| [04_rl_training](notebooks/04_rl_training.ipynb) | Gymnasium + PPO 训练 |
| [05_data_collection](notebooks/05_data_collection.ipynb) | 轨迹录制，导出到 LeRobot |

---

## 路线图

- [x] **Phase 1**: ESP32 固件 + ROS2 栈 + 硬件设计
- [x] **Phase 1**: `threewe` Python API + Sim2Real 后端
- [x] **Phase 1**: Gymnasium 环境 + VLM/VLA 集成
- [x] **Phase 1**: 基准测试框架 + 示例脚本
- [x] **Phase 2**: 机载状态显示面板（1.3" OLED SH1106，3键导航，5页状态，故障码）
- [ ] **Phase 2**: Isaac Sim 后端
- [ ] **Phase 2**: 硬件抽象层（支持第三方机器人）
- [ ] **Phase 2**: 基础模型微调流水线
- [ ] **Phase 3**: 3we Hub（模型/数据集共享）
- [ ] **Phase 3**: 多机器人协同管理

---

## 许可证

| 组件 | 许可证 | 文件 |
|:-----|:-------|:-----|
| 固件与软件 | Apache License 2.0 | [`LICENSE`](LICENSE) |
| 硬件设计 | CERN-OHL-P v2 | [`LICENSE-HARDWARE`](LICENSE-HARDWARE) |
| 文档 | CC BY-SA 4.0 | [`LICENSE-DOCS`](LICENSE-DOCS) |

---

## 参与贡献

欢迎贡献！请查阅 **[CONTRIBUTING.md](CONTRIBUTING.md)** 了解开发环境搭建、分支策略和 PR 流程。

---

## 安全须知

> [!WARNING]
> 本平台包含**运动机械部件**和**锂电池**。

- 每次操作前务必确认急停按钮功能正常
- 请勿旁路或修改安全继电器电路
- 遵循文档中的电池处理指南

---

<div align="center">

**[English](README.md) | [中文](README_zh.md)**

</div>
