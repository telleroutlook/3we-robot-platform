<div align="center">

# Robot Platform

**通用模块化移动平台**

[![License](https://img.shields.io/badge/代码-Apache_2.0-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/硬件-CERN--OHL--P_v2-green.svg)](LICENSE-HARDWARE)
[![License](https://img.shields.io/badge/文档-CC_BY--SA_4.0-orange.svg)](LICENSE-DOCS)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%20|%20Jazzy-blueviolet.svg)](https://ros.org/)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.x-red.svg)](https://github.com/espressif/esp-idf)

一个开源的全向移动机器人平台，<br/>
专为**模块化**、**可扩展性**和**快速载荷集成**而设计。

[快速开始](#-快速开始) &bull;
[文档](docs/) &bull;
[参与贡献](CONTRIBUTING.md) &bull;
[硬件设计](hardware/)

**[English](README.md) | [中文](README_zh.md)**

</div>

---

> [!NOTE]
> 本项目正在积极开发中，硬件设计和固件正在验证阶段。

<br/>

## ✦ 核心能力

<table>
<tr>
<td width="50%">

**运动与控制**
- 全向麦克纳姆轮驱动
- 闭环 PID 编码器反馈
- 50 Hz 控制回路，延迟 < 20 ms
- 可配置速度限制（最大 1.2 m/s）

</td>
<td width="50%">

**智能与导航**
- 边缘 AI 推理（Hailo-8/8L）
- Nav2 自主导航
- slam_toolbox 实时建图
- ROS2 原生集成

</td>
</tr>
<tr>
<td>

**安全与加密**
- ISO 13850 硬件急停按钮
- 双通道安全继电器（带自检）
- DTLS 1.2 加密通信
- Ed25519 签名 OTA 升级

</td>
<td>

**模块化与可扩展**
- PBC-34 热插拔载荷总线
- EEPROM 自动识别
- 电源时序控制与功率预算管理
- 多协议：Wi-Fi / BLE / 4G / 5G / LoRa

</td>
</tr>
</table>

<br/>

## ✦ 产品线

| | **Basic** | **Standard** | **Pro** | **Industrial** |
|:--|:--:|:--:|:--:|:--:|
| **定位** | 教育 | 科研 | 商业 | 工业 |
| **AI 算力** | — | Hailo-8L (13 TOPS) | Hailo-8 (26 TOPS) | Hailo-8 (26 TOPS) |
| **通信** | Wi-Fi + BLE | Wi-Fi + BLE | + 4G | + 5G + LoRa |
| **CAN 总线** | — | — | — | MCP2515 + TJA1050 |
| **防护等级** | IP20 | IP20 | IP40 | IP65 |

<br/>

## ✦ 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                        载荷层                               │
│              用户设备通过 PBC-34 连接器接入                   │
├───────────────────────────────────────────────────────────┤
│                        应用层                               │
│          ROS2  ·  Nav2  ·  SLAM  ·  自定义节点              │
├───────────────────────────────────────────────────────────┤
│                        计算层                               │
│          Raspberry Pi 5  +  AI 加速器 (Hailo)              │
├───────────────────────────────────────────────────────────┤
│                        固件层                               │
│     ESP32-S3  ·  电机  ·  传感器  ·  安全  ·  通信          │
├───────────────────────────────────────────────────────────┤
│                        硬件层                               │
│    麦克纳姆轮  ·  DRV8833  ·  电池  ·  急停按钮             │
└───────────────────────────────────────────────────────────┘
```

<br/>

## ✦ 仓库结构

```
robot-platform/
│
├── firmware/                    # ESP32-S3 固件 (ESP-IDF + micro-ROS)
│   ├── esp32/main/             #   应用源码
│   └── config/                 #   引脚定义、机器人参数
│
├── ros2_ws/                    # ROS2 工作空间
│   ├── robot_bringup/          #   启动文件、Nav2/SLAM 配置
│   ├── robot_description/      #   URDF 模型 (Xacro)
│   └── robot_interfaces/       #   自定义消息/服务定义
│
├── hardware/                   # 硬件设计
│   ├── pcb/                    #   PCB 规格、PBC-34 引脚表
│   ├── structure/              #   结构设计图纸
│   └── bom/                    #   物料清单（4 个 SKU）
│
├── sdk/                        # 载荷开发工具包
│   ├── payload_interface/      #   Python 通信库
│   ├── tools/                  #   EEPROM 验证工具
│   ├── examples/               #   参考实现
│   └── web_basic/              #   浏览器遥控界面
│
└── docs/                       # 文档
    ├── assembly_guide.md       #   硬件组装指南
    ├── firmware_flash.md       #   编译与烧录指南
    ├── payload_dev_guide.md    #   载荷开发教程
    ├── compliance_checklist.md #   法规合规检查清单
    └── performance_benchmarks.md
```

<br/>

## ✦ 快速开始

### 前置要求

| 工具 | 版本 | 用途 |
|------|------|------|
| [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/) | v5.x | 固件编译工具链 |
| [ROS2](https://docs.ros.org/en/humble/Installation.html) | Humble / Jazzy | 机器人中间件 |
| Python | 3.10+ | SDK 与工具 |
| [KiCad](https://www.kicad.org/) | 8+ | 硬件修改（可选） |

### 1. 编译并烧录固件

```bash
cd firmware/esp32
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

### 2. 编译 ROS2 工作空间

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 3. 启动机器人

```bash
ros2 launch robot_bringup robot.launch.py
```

<br/>

## ✦ 技术栈

| 层级 | 技术选型 | 角色 |
|:-----|:---------|:-----|
| 微控制器 | ESP32-S3 | 双核 240 MHz，Wi-Fi + BLE |
| 单板机 | Raspberry Pi 5 (8 GB) | ROS2、导航、视觉 |
| AI 加速 | Hailo-8L / Hailo-8 | 13–26 TOPS 边缘推理 |
| 实时系统 | FreeRTOS (ESP-IDF) | 电机与传感器实时控制 |
| 中间件 | micro-ROS ↔ ROS2 | MCU–SBC 桥接 |
| 导航 | Nav2 + slam_toolbox | SLAM 与路径规划 |
| 电机驱动 | DRV8833 x2 | 4 路直流电机 H 桥 |
| 安全加密 | DTLS 1.2 + Ed25519 OTA | 加密控制、签名升级 |
| 安全系统 | ISO 13850 急停 | 硬件互锁 |

<br/>

## ✦ 许可证

本项目采用 **Open Core** 多许可证结构：

| 组件 | 许可证 | 文件 |
|:-----|:-------|:-----|
| 固件与软件 | Apache License 2.0 | [`LICENSE`](LICENSE) |
| 硬件设计 | CERN-OHL-P v2 | [`LICENSE-HARDWARE`](LICENSE-HARDWARE) |
| 文档 | CC BY-SA 4.0 | [`LICENSE-DOCS`](LICENSE-DOCS) |

第三方依赖声明：[`NOTICE`](NOTICE)

<br/>

## ✦ 参与贡献

欢迎参与贡献！请查阅 **[CONTRIBUTING.md](CONTRIBUTING.md)** 了解：

- 开发环境搭建
- 分支策略与规范化提交
- Pull Request 流程
- 安全关键贡献规则

<br/>

## ✦ 安全须知

> [!WARNING]
> 本平台包含**运动机械部件**和**锂电池**，操作前请注意安全。

- 每次操作前务必确认急停按钮功能正常
- 请勿旁路或修改安全继电器电路
- 遵循文档中的电池处理指南
- 运行时远离轮组

<br/>

## ✦ 社区与支持

| 渠道 | 用途 |
|------|------|
| [GitHub Issues](../../issues) | Bug 报告、功能请求 |
| [GitHub Discussions](../../discussions) | 问题讨论、创意交流 |

<br/>

## ✦ 致谢

本项目基于以下优秀开源项目构建：

| 项目 | 维护者 |
|------|--------|
| [ESP-IDF](https://github.com/espressif/esp-idf) | Espressif Systems |
| [micro-ROS](https://micro.ros.org/) | eProsima |
| [ROS 2](https://ros.org/) | Open Robotics |
| [Nav2](https://nav2.org/) | Steve Macenski 等 |
| [KiCad](https://www.kicad.org/) | KiCad 社区 |

---

<div align="center">
<sub>为机器人社区用心打造。</sub>
</div>
