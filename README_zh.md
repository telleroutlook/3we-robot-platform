<div align="center">

# 3WE Robot Platform

**通用模块化移动平台**

[![License](https://img.shields.io/badge/代码-Apache_2.0-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/硬件-CERN--OHL--P_v2-green.svg)](LICENSE-HARDWARE)
[![License](https://img.shields.io/badge/文档-CC_BY--SA_4.0-orange.svg)](LICENSE-DOCS)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%20|%20Jazzy-blueviolet.svg)](https://ros.org/)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.x-red.svg)](https://github.com/espressif/esp-idf)

[![ESP32-S3](https://img.shields.io/badge/ESP32--S3-000000?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/en/products/socs/esp32-s3)
[![ROS2](https://img.shields.io/badge/ROS2-22314E?style=for-the-badge&logo=ros&logoColor=white)](https://ros.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![KiCad](https://img.shields.io/badge/KiCad-314CB0?style=for-the-badge&logo=kicad&logoColor=white)](https://www.kicad.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/3we/robot-platform/full-validation.yml?style=for-the-badge&label=CI)](../../actions)

一个开源的全向移动机器人平台，<br/>
专为**模块化**、**可扩展性**和**快速载荷集成**而设计。

<img src="docs/images/robot-platform-hero.png" alt="机器人平台" width="600"/>

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

## ✦ 为什么选择本项目

| 痛点 | 我们的解决方案 |
|:-----|:---------------|
| 从零搭建机器人平台需要数月时间 | 完整开源技术栈：硬件 → 固件 → ROS2 → SDK，开箱即用可定制 |
| 多数平台硬件设计闭源 | 完全开放 PCB（KiCad）+ 机械图纸，采用 CERN-OHL-P 许可 |
| 没有标准化的载荷接口 | PBC-34 热插拔总线 + EEPROM 自动识别 —— 插入传感器即刻工作 |
| 教育平台无法扩展到工业场景 | 4 个 SKU 从教室（Basic）到工厂（Industrial）—— 同一代码库 |
| 安全性往往是事后补救 | DTLS 1.2 加密通信 + 签名 OTA + 硬件急停，从第一天就内置 |

### 适合谁？

- **学生与教育者** —— 用生产级代码学习真正的嵌入式系统、ROS2 和机电一体化，而非玩具示例
- **科研人员** —— 跳过 6 个月的平台搭建期；在经过验证的传感器融合底盘上专注你的算法
- **产品开发者** —— 从原型到产品用同一平台；切换 SKU 配置无需重写代码
- **工业集成商** —— IP65 防护、CAN 总线、5G、硬件安全继电器 —— 自信部署到真实场景

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
│   ├── robot_diagnostics/      #   健康监控、指标导出
│   ├── robot_interfaces/       #   自定义消息/服务定义
│   ├── robot_perception/       #   摄像头 + AI 推理 (Hailo)
│   └── robot_simulation/       #   Gazebo 仿真
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
│   ├── web_control/            #   TypeScript Web 组件 (Lit)
│   └── web_basic/              #   浏览器遥控界面
│
└── docs/                       # 文档
    ├── assembly_guide.md       #   硬件组装指南
    ├── firmware_guide.md        #   编译与烧录指南
    ├── pbc34_payload_guide.md  #   载荷开发完整参考
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

## ✦ 与竞品对比

| 特性 | **本项目** | TurtleBot 4 | Linorobot2 | ROSbot XL | Yahboom X3 |
|:-----|:---:|:---:|:---:|:---:|:---:|
| **开放硬件** | 完全开放 (CERN-OHL-P) | 部分 | 部分 | 闭源 | 闭源 |
| **麦轮驱动** | 四轮全向 | 差速 | 可配置 | 麦轮 | 麦轮 |
| **载荷系统** | PBC-34 热插拔总线 | USB/串口 | 无 | GPIO 排针 | 无 |
| **加密通信** | DTLS 1.2 | 无 | 无 | 无 | 无 |
| **多 SKU** | 4 个变体（同一代码库） | 单一 | 单一 | 2 个变体 | 单一 |
| **Web 控制** | 内置（TypeScript） | 需 RViz | 无 | ROSbot UI | 仅 App |
| **硬件安全继电器** | ISO 13850 + 自检 | 仅软件 | 无 | 仅软件 | 无 |

本平台占据独特定位：**完全开放硬件 + 生产级安全**，填补了教育套件与闭源工业机器人之间的空白。没有其他开源平台能在单一架构中同时提供标准化载荷总线、加密通信和多 SKU 可扩展性。

> 详细多维度对比请参见 **[docs/competitive_analysis.md](docs/competitive_analysis.md)**。

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
