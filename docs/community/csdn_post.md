---
Platform: CSDN
Type: 博客文章
---

# 开源：一个 $300 的 ROS2 机器人平台，Python SDK 零代码切换仿真与真机

## 前言

我最近在做一个开源机器人平台，目标是让 AI 研究者用 Python 就能控制机器人——不需要懂 ROS2、不需要写 launch 文件、不需要调 tf tree。同一份代码在模拟和真机上零修改运行。

硬件成本 < $500（约 ¥3500），全部开源：PCB 源文件（KiCad）、BOM、组装文档、固件、ROS2 包、Python SDK。

GitHub：https://github.com/telleroutlook/3we-robot-platform

## 30 秒体验（不需要任何硬件）

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

只需要 Python 3.10+ 和 numpy。Mock 后端在纯 Python 里模拟 2D 运动学、碰撞检测、360° LiDAR 光线投射。不是返回假数据，是真正在计算。

## 核心 API

```python
from threewe import Robot

async with Robot(backend="mock") as robot:
    # 导航到目标点
    await robot.move_to(x=3.0, y=2.0)
    
    # 获取传感器数据
    scan = robot.get_lidar_scan()  # 360维 numpy 数组
    pose = robot.get_pose()        # 带类型的 NamedTuple
    imu = robot.get_imu()
    
    # VLM 自然语言控制（需要 pip install threewe[ai]）
    await robot.execute_instruction("去红色门那里")
```

把 `backend="mock"` 换成 `"gazebo"` 或 `"real"`——零代码修改。

## 架构

```
┌──────────────────────────────────────────────┐
│           你的 Python 代码                     │
│  robot.move_to() · robot.get_image()         │
├──────────────────────────────────────────────┤
│           threewe Python SDK                  │
│  Robot · Types · Gym · AI(VLM/VLA) · Data    │
├────────────┬─────────────┬───────────────────┤
│ MockBackend│ GazeboBackend│ RealBackend       │
│ (numpy)    │ (ros_gz)     │ (rclpy)          │
├────────────┴─────────────┴───────────────────┤
│           ROS2 Jazzy + Nav2                   │
├──────────────────────────────────────────────┤
│           固件 (ESP32-S3 + micro-ROS)         │
├──────────────────────────────────────────────┤
│           硬件层                              │
│  麦克纳姆轮 · DRV8833 · LD06 LiDAR · BNO055  │
└──────────────────────────────────────────────┘
```

## 硬件配置

| 规格 | 参数 |
|:-----|:-----|
| 驱动 | 4轮麦克纳姆（65mm），全向移动 |
| MCU | ESP32-S3（双核 240MHz） |
| SBC | Raspberry Pi 5（8GB） |
| AI 加速 | Hailo-8L（13 TOPS） |
| LiDAR | LD06（360°，12m 量程） |
| IMU | BNO055（9轴融合） |
| 电池 | 7.4V 锂电，约 2h 续航 |
| 安全 | ISO 13850 急停 + 双通道继电器 |
| 成本 | < ¥3500 |

## 为什么做这个

现有方案的痛点：

- **TurtleBot 4**：~$1200，必须懂 ROS2 才能用，没有 Python 优先的 API
- **LeRobot**：专注机械臂，不适合移动机器人导航
- **Isaac Lab**：强大但绑定 NVIDIA GPU，门槛高

我想要的是：AI 研究者 `pip install` 之后就能开始训练 RL 策略或跑 VLM 实验，不需要花两周配 ROS2 环境。

## 当前状态（诚实说明）

**已完成：**
- ✅ ESP32-S3 固件（micro-ROS，电机 PID，编码器里程计）
- ✅ ROS2 包（Nav2 集成，SLAM，Gazebo 仿真配置）
- ✅ Python SDK + Mock 后端（309 个测试通过）
- ✅ Gymnasium 环境 `3we/Navigation-v1`
- ✅ VLM 集成（GPT-4o / Qwen-VL → 机器人动作）
- ✅ HDF5 轨迹记录

**进行中：**
- 🔄 Gazebo 后端集成测试
- 🔄 PyPI 发布（目前从源码安装）
- 🔄 真机 Sim2Real 验证

**未开始：**
- ❌ Isaac Sim 后端
- ❌ 多机器人编队
- ❌ 模型微调流水线

## RL 训练示例

```python
import gymnasium
import threewe.gym

env = gymnasium.make("3we/Navigation-v1")
obs, info = env.reset()

for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

观测空间：360 维 LiDAR + 2D 位姿 + 速度
动作空间：连续 `[vx, vy, omega]`（全向）

## 工程决策记录

为什么选 ESP32-S3 而不是 STM32？为什么用麦克纳姆轮？PBC-34 载荷总线原型踩了哪些坑？

详细记录在开发日志：https://3we.org/blog/dev-log-001/

## 开源协议

| 组件 | 协议 |
|:-----|:-----|
| 固件 & 软件 | Apache 2.0 |
| 硬件设计 | CERN-OHL-P v2 |
| 文档 | CC BY-SA 4.0 |

## 希望得到的反馈

1. SDK API 设计是否符合你的使用习惯？
2. Gymnasium 环境的观测/动作空间还需要什么？
3. 如果你在做移动机器人 RL 或 VLM 研究，什么功能能让你真正用起来？

---

项目地址：https://github.com/telleroutlook/3we-robot-platform
开发博客：https://3we.org/blog/overview/
