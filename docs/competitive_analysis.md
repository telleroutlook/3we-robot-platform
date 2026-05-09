<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Competitive Analysis / 竞品分析

> **Last updated**: 2025-01  
> This document compares the Robot Platform against prominent open-source and commercial mobile robot platforms.

---

## Platforms Compared

| # | Platform | Maintainer | Drive Type | Price Range (USD) |
|:-:|:---------|:-----------|:-----------|:-----------------:|
| 1 | **Robot Platform (This Project)** | 3we (open-source) | 4WD Mecanum | $200–$800 |
| 2 | TurtleBot 4 | Clearpath / Open Robotics | Differential (iRobot Create 3) | $1,200–$2,000 |
| 3 | Linorobot2 | linorobot (community) | Differential / Mecanum / Ackermann | $300–$600 |
| 4 | ROSbot XL | Husarion | Mecanum | $2,800–$3,500 |
| 5 | Yahboom X3 Plus | Yahboom | Mecanum | $400–$700 |
| 6 | JetBot | NVIDIA | Differential | $150–$300 |
| 7 | OpenMower | community | Differential (lawn) | $500–$1,000 |
| 8 | Rover Robotics (Rover Zero) | Rover Robotics | Skid-steer | $3,000+ |

---

## Multi-Dimensional Comparison

### Hardware Openness

| Platform | PCB Design | Mechanical CAD | License | Manufacturability |
|:---------|:---:|:---:|:---:|:---:|
| **This Project** | Full KiCad source | Full drawings | CERN-OHL-P v2 | BOM for 4 SKUs |
| TurtleBot 4 | Closed (Create 3 base) | URDF only | — | Must buy assembled |
| Linorobot2 | Reference schematic | 3D-printed parts | MIT | DIY-friendly |
| ROSbot XL | Closed | STEP export only | Proprietary | Must buy assembled |
| Yahboom X3 | Closed | None | Proprietary | Must buy assembled |
| JetBot | Open (simple) | 3D-printed chassis | MIT | DIY-friendly |
| OpenMower | Full KiCad source | Full CAD | CC-BY-NC-SA | Requires donor mower |
| Rover Zero | Closed | None | Proprietary | Must buy assembled |

### Software Stack

| Platform | MCU Firmware | ROS2 Support | Navigation | Web UI |
|:---------|:---:|:---:|:---:|:---:|
| **This Project** | ESP-IDF + micro-ROS | Native (Humble/Jazzy) | Nav2 + slam_toolbox | Built-in TypeScript |
| TurtleBot 4 | Closed (Create 3) | Native | Nav2 | Via RViz only |
| Linorobot2 | Arduino / Teensy | Native | Nav2 | None |
| ROSbot XL | Closed (STM32) | Native | Nav2 | Husarion WebUI |
| Yahboom X3 | Arduino | Basic (ROS1 primary) | Basic SLAM | Mobile app |
| JetBot | None (direct GPIO) | Community packages | Basic | Jupyter notebook |
| OpenMower | Custom STM32 | Partial | Custom planner | Web dashboard |
| Rover Zero | Closed | Native | Nav2 | None |

### Security & Safety

| Platform | Encrypted Comms | Signed OTA | HW Emergency Stop | Safety Relay | Payload Isolation |
|:---------|:---:|:---:|:---:|:---:|:---:|
| **This Project** | DTLS 1.2 | Ed25519 | ISO 13850 | Dual-channel + self-test | Sandboxed |
| TurtleBot 4 | None | None | Soft button | None | None |
| Linorobot2 | None | None | None | None | None |
| ROSbot XL | None | Husarion cloud | Software E-stop | None | None |
| Yahboom X3 | None | None | None | None | None |
| JetBot | None | None | None | None | None |
| OpenMower | None | None | Blade stop | Simple relay | None |
| Rover Zero | None | None | HW E-stop | Basic relay | None |

### Payload & Extensibility

| Platform | Payload Interface | Hot-plug | Auto-Discovery | Power Management | Multi-SKU |
|:---------|:---:|:---:|:---:|:---:|:---:|
| **This Project** | PBC-34 bus (I2C+SPI+UART+Power) | Yes | EEPROM identification | Sequenced, budget-managed | 4 SKUs |
| TurtleBot 4 | USB + Create 3 port | No | None | None | 2 configs |
| Linorobot2 | Breadboard / GPIO | No | None | None | Single |
| ROSbot XL | GPIO header + USB | No | None | Basic | 2 configs |
| Yahboom X3 | GPIO pin header | No | None | None | Single |
| JetBot | Jetson GPIO | No | None | None | Single |
| OpenMower | Custom connector | No | None | None | Single |
| Rover Zero | USB + Ethernet | No | None | Built-in | 3 models |

### Scalability (Education → Industry)

| Platform | Education | Research | Commercial | Industrial |
|:---------|:---:|:---:|:---:|:---:|
| **This Project** | Basic SKU | Standard SKU | Pro SKU (4G) | Industrial SKU (5G, CAN, IP65) |
| TurtleBot 4 | Lite version | Standard | — | — |
| Linorobot2 | Good fit | Good fit | — | — |
| ROSbot XL | — | Good fit | Possible | — |
| Yahboom X3 | Good fit | Limited | — | — |
| JetBot | Good fit | Limited | — | — |
| OpenMower | — | Niche | — | — |
| Rover Zero | — | Possible | Good fit | Outdoor |

---

## Unique Positioning

```
                    Open Hardware
                         ↑
                         │
         OpenMower   ●   │   ● This Project
         Linorobot2  ●   │
                         │
  ← Education ───────────┼──────────── Industrial →
                         │
                 JetBot ●│
         Yahboom X3   ●  │   ● ROSbot XL
                         │          ● Rover Zero
            TurtleBot 4 ●│
                         │
                         ↓
                   Closed Hardware
```

**This project is the only platform in the upper-right quadrant**: fully open hardware that scales to industrial deployment. All other open-hardware platforms target education/research only, while industrial-capable platforms are proprietary.

---

## Key Differentiators

1. **PBC-34 Payload Bus** — No other platform offers a standardized, hot-pluggable, auto-discovering payload interface. This dramatically reduces integration time for custom sensors, actuators, and compute modules.

2. **Security-First Architecture** — The only open-source mobile robot with DTLS encrypted communication, cryptographically signed OTA, and hardware safety interlocks meeting ISO 13850.

3. **Single Codebase, Four Products** — Build-time SKU selection via `sdkconfig` overlays means one repository produces platforms ranging from $200 classroom kits to IP65 industrial units.

4. **Full-Stack Openness** — From KiCad schematics to ROS2 launch files to TypeScript web UI — everything is open, auditable, and forkable under permissive licenses.

5. **Production-Ready from Day One** — Secure boot, flash encryption, NVS encryption, structured logging, fleet OTA strategy — not bolted on later but designed into the architecture.

---
---

# 竞品分析（中文）

> **最后更新**：2025-01  
> 本文档将 Robot Platform 与主流开源及商业移动机器人平台进行对比。

---

## 对比平台一览

| # | 平台 | 维护者 | 驱动方式 | 价格区间 (USD) |
|:-:|:-----|:-------|:---------|:--------------:|
| 1 | **Robot Platform（本项目）** | 3we（开源） | 四轮麦克纳姆 | $200–$800 |
| 2 | TurtleBot 4 | Clearpath / Open Robotics | 差速（iRobot Create 3） | $1,200–$2,000 |
| 3 | Linorobot2 | linorobot（社区） | 差速 / 麦轮 / 阿克曼 | $300–$600 |
| 4 | ROSbot XL | Husarion | 麦克纳姆 | $2,800–$3,500 |
| 5 | Yahboom X3 Plus | Yahboom | 麦克纳姆 | $400–$700 |
| 6 | JetBot | NVIDIA | 差速 | $150–$300 |
| 7 | OpenMower | 社区 | 差速（草坪） | $500–$1,000 |
| 8 | Rover Robotics (Rover Zero) | Rover Robotics | 滑差转向 | $3,000+ |

---

## 多维度对比

### 硬件开放程度

| 平台 | PCB 设计 | 机械 CAD | 许可证 | 可制造性 |
|:-----|:---:|:---:|:---:|:---:|
| **本项目** | 完整 KiCad 源文件 | 完整图纸 | CERN-OHL-P v2 | 4 个 SKU 的 BOM |
| TurtleBot 4 | 闭源（Create 3 底盘） | 仅 URDF | — | 需购买成品 |
| Linorobot2 | 参考原理图 | 3D 打印零件 | MIT | DIY 友好 |
| ROSbot XL | 闭源 | 仅 STEP 导出 | 专有 | 需购买成品 |
| Yahboom X3 | 闭源 | 无 | 专有 | 需购买成品 |
| JetBot | 开源（简单） | 3D 打印底盘 | MIT | DIY 友好 |
| OpenMower | 完整 KiCad 源文件 | 完整 CAD | CC-BY-NC-SA | 需要捐赠割草机 |
| Rover Zero | 闭源 | 无 | 专有 | 需购买成品 |

### 软件栈

| 平台 | MCU 固件 | ROS2 支持 | 导航能力 | Web 界面 |
|:-----|:---:|:---:|:---:|:---:|
| **本项目** | ESP-IDF + micro-ROS | 原生（Humble/Jazzy） | Nav2 + slam_toolbox | 内置 TypeScript |
| TurtleBot 4 | 闭源（Create 3） | 原生 | Nav2 | 仅 RViz |
| Linorobot2 | Arduino / Teensy | 原生 | Nav2 | 无 |
| ROSbot XL | 闭源（STM32） | 原生 | Nav2 | Husarion WebUI |
| Yahboom X3 | Arduino | 基础（主要 ROS1） | 基础 SLAM | 手机 App |
| JetBot | 无（直接 GPIO） | 社区包 | 基础 | Jupyter notebook |
| OpenMower | 自定义 STM32 | 部分 | 自定义规划器 | Web 面板 |
| Rover Zero | 闭源 | 原生 | Nav2 | 无 |

### 安全性

| 平台 | 加密通信 | 签名 OTA | 硬件急停 | 安全继电器 | 载荷隔离 |
|:-----|:---:|:---:|:---:|:---:|:---:|
| **本项目** | DTLS 1.2 | Ed25519 | ISO 13850 | 双通道 + 自检 | 沙箱隔离 |
| TurtleBot 4 | 无 | 无 | 软件按钮 | 无 | 无 |
| Linorobot2 | 无 | 无 | 无 | 无 | 无 |
| ROSbot XL | 无 | Husarion 云 | 软件急停 | 无 | 无 |
| Yahboom X3 | 无 | 无 | 无 | 无 | 无 |
| JetBot | 无 | 无 | 无 | 无 | 无 |
| OpenMower | 无 | 无 | 刀片停止 | 简单继电器 | 无 |
| Rover Zero | 无 | 无 | 硬件急停 | 基础继电器 | 无 |

### 载荷与可扩展性

| 平台 | 载荷接口 | 热插拔 | 自动发现 | 电源管理 | 多 SKU |
|:-----|:---:|:---:|:---:|:---:|:---:|
| **本项目** | PBC-34 总线 (I2C+SPI+UART+Power) | 支持 | EEPROM 识别 | 时序控制、功率预算 | 4 个 SKU |
| TurtleBot 4 | USB + Create 3 端口 | 不支持 | 无 | 无 | 2 种配置 |
| Linorobot2 | 面包板 / GPIO | 不支持 | 无 | 无 | 单一 |
| ROSbot XL | GPIO 排针 + USB | 不支持 | 无 | 基础 | 2 种配置 |
| Yahboom X3 | GPIO 排针 | 不支持 | 无 | 无 | 单一 |
| JetBot | Jetson GPIO | 不支持 | 无 | 无 | 单一 |
| OpenMower | 自定义连接器 | 不支持 | 无 | 无 | 单一 |
| Rover Zero | USB + 以太网 | 不支持 | 无 | 内置 | 3 种型号 |

### 可扩展性（教育 → 工业）

| 平台 | 教育 | 科研 | 商业 | 工业 |
|:-----|:---:|:---:|:---:|:---:|
| **本项目** | Basic SKU | Standard SKU | Pro SKU (4G) | Industrial SKU (5G, CAN, IP65) |
| TurtleBot 4 | Lite 版本 | Standard | — | — |
| Linorobot2 | 适合 | 适合 | — | — |
| ROSbot XL | — | 适合 | 可能 | — |
| Yahboom X3 | 适合 | 有限 | — | — |
| JetBot | 适合 | 有限 | — | — |
| OpenMower | — | 细分领域 | — | — |
| Rover Zero | — | 可能 | 适合 | 户外 |

---

## 独特定位

```
                    开放硬件
                       ↑
                       │
       OpenMower   ●   │   ● 本项目
       Linorobot2  ●   │
                       │
  ← 教育 ──────────────┼──────────── 工业 →
                       │
               JetBot ●│
       Yahboom X3   ●  │   ● ROSbot XL
                       │          ● Rover Zero
          TurtleBot 4 ●│
                       │
                       ↓
                    闭源硬件
```

**本项目是唯一位于右上象限的平台**：完全开放的硬件设计，同时能扩展到工业部署。所有其他开放硬件平台仅面向教育/科研，而具备工业能力的平台都是专有的。

---

## 核心差异化优势

1. **PBC-34 载荷总线** —— 没有其他平台提供标准化的、可热插拔的、自动发现的载荷接口。这大幅减少了自定义传感器、执行器和计算模块的集成时间。

2. **安全优先架构** —— 唯一提供 DTLS 加密通信、密码学签名 OTA 和符合 ISO 13850 硬件安全互锁的开源移动机器人。

3. **一套代码，四款产品** —— 通过 `sdkconfig` 叠加层在编译时选择 SKU，同一仓库可生产从 $200 教学套件到 IP65 工业单元的全线产品。

4. **全栈开放** —— 从 KiCad 原理图到 ROS2 启动文件再到 TypeScript Web 界面 —— 一切开放、可审计、可 Fork，采用宽松许可证。

5. **从第一天就生产就绪** —— 安全启动、Flash 加密、NVS 加密、结构化日志、车队 OTA 策略 —— 不是事后补救，而是架构设计的一部分。
