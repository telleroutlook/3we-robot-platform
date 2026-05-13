# Bill of Materials (BOM)

> SPDX-License-Identifier: CERN-OHL-P-2.0

Complete parts list for building a 3we robot. Three hardware tiers available — start with Basic for learning, upgrade to Standard for AI research.

---

## Cost Summary

| SKU | Target User | Total Cost (CNY) | Total Cost (USD) | Key Capability |
|:----|:-----------|:-----------------|:-----------------|:---------------|
| **Basic** | Students, hobbyists | ~¥680 | ~$95 | ESP32 teleop, encoder feedback, ultrasonic |
| **Standard** | AI/ML researchers | ~¥2,200 | ~$300 | Pi 5 + Hailo-8L, full ROS2, VLM inference |
| **Standard + LiDAR** | Navigation research | ~¥2,500 | ~$345 | + 2D SLAM, Nav2 autonomous navigation |
| **Industrial** | Production/fleet | ~¥4,500 | ~$620 | 5G, CAN, IP54, heavy payload |

*Prices as of 2026-05. Exchange rate: 1 USD ≈ 7.2 CNY.*

---

## Purchase Strategy

### Where to Buy

| Supplier | What to Buy | Shipping (China) | Shipping (Intl.) | Notes |
|:---------|:-----------|:-----------------|:-----------------|:------|
| **LCSC (立创商城)** | All SMD components, connectors, passives | 1-2 days | 5-10 days (via lcsc.com) | Best for electronics. Free shipping >¥50 |
| **Taobao (淘宝)** | Motors, wheels, batteries, mechanical | 2-3 days | Use forwarding agent | Search keywords provided below |
| **AliExpress** | Same as Taobao, English interface | N/A | 7-20 days | Higher markup than Taobao (~20-30%) |
| **Pimoroni** | Raspberry Pi 5, official accessories | N/A | 3-7 days (UK/EU/US) | Official Pi distributor |
| **Hailo Store** | Hailo-8L M.2 module | N/A | 5-10 days | Direct from manufacturer |

### Taobao/AliExpress Search Keywords

| Part | Chinese Keywords | English Keywords (AliExpress) |
|:-----|:----------------|:-----------------------------|
| N20 Motor with encoder | `N20减速电机 编码器 6V 1:50` | `N20 gear motor encoder 6V 1:50 ratio` |
| 48mm Mecanum wheel | `48mm麦克纳姆轮 铝合金` | `48mm mecanum wheel aluminum hub` |
| 65mm Mecanum wheel | `65mm麦克纳姆轮 铝合金 PU滚子` | `65mm mecanum wheel aluminum PU roller` |
| 18650 battery holder 2S | `18650电池盒 2串 带BMS` | `18650 battery holder 2S with BMS` |
| E-stop mushroom button | `急停按钮 φ30 常闭 蘑菇头` | `emergency stop button 30mm NC mushroom` |
| LD06 LiDAR | `乐动LD06激光雷达` | `LD06 LiDAR 360 degree laser scanner` |
| USB fisheye camera 170° | `USB广角摄像头 170度 1080P` | `USB fisheye camera 170 degree 1080P` |
| 5V fan 30×30mm | `3010风扇 5V` | `30mm 5V cooling fan 3010` |

---

## SKU Details

### Basic SKU (~¥680 / $95)

Self-contained ESP32-S3 platform for learning motor control, sensor fusion, and embedded programming.

| Ref | Component | Qty | Unit ¥ | Subtotal ¥ | Source |
|:----|:----------|:----|:-------|:-----------|:-------|
| U1 | ESP32-S3-WROOM-1-N8R8 | 1 | 28 | 28 | LCSC |
| U2 | DRV8833 motor driver | 2 | 6.50 | 13 | LCSC |
| U3 | AMS1117-3.3 LDO | 1 | 0.80 | 0.80 | LCSC |
| U4 | MT3608 boost converter | 1 | 1.20 | 1.20 | LCSC |
| U5 | MP1584EN buck converter | 1 | 3.50 | 3.50 | LCSC |
| U6 | MCP23017 GPIO expander | 1 | 8.50 | 8.50 | LCSC |
| U7 | INA219 power monitor | 1 | 5.80 | 5.80 | LCSC |
| M1-4 | N20 1:90 motor + encoder | 4 | 18 | 72 | Taobao |
| W1-4 | 48mm Mecanum wheels | 4 | 25 | 100 | Taobao |
| S1-4 | HC-SR04 ultrasonic | 4 | 4.50 | 18 | LCSC |
| IMU1 | BNO055 IMU module | 1 | 45 | 45 | LCSC |
| BAT1 | 2S 18650 + BMS | 1 | 35 | 35 | Taobao |
| SW1 | E-stop button (NC) | 1 | 8 | 8 | Taobao |
| RLY1 | Safety relay dual-CH | 1 | 15 | 15 | Taobao |
| J1 | PBC-34 connector pair | 2 | 5 | 10 | LCSC |
| J2 | XT30 connector | 2 | 2.50 | 5 | LCSC |
| J3 | USB-C receptacle | 1 | 1.50 | 1.50 | LCSC |
| — | Passives (caps, resistors, etc.) | lot | — | ~15 | LCSC |
| — | PCB fabrication (JLCPCB) | 5pcs | — | ~50 | JLCPCB |
| — | Chassis (aluminum cut or 3D print) | 1 | — | ~150 | Taobao |
| — | Wires, screws, standoffs | lot | — | ~30 | LCSC/Taobao |
| | | | **Total** | **~¥680** | |

### Standard SKU Upgrade (+~¥1,520 on top of Basic)

Adds AI compute capability for full Python API, ROS2, VLM/VLA inference.

| Ref | Component | Qty | Unit ¥ | Subtotal ¥ | Source |
|:----|:----------|:----|:-------|:-----------|:-------|
| SBC1 | Raspberry Pi 5 (8GB) | 1 | 595 | 595 | Pimoroni |
| AI1 | Hailo-8L M.2 module | 1 | 580 | 580 | Hailo |
| HAT1 | AI HAT+ (M.2 carrier) | 1 | 198 | 198 | Pimoroni |
| CAM1 | USB fisheye 170° 1080P | 1 | 85 | 85 | Taobao |
| MOT1-4 | N20 1:50 motors (upgrade) | 4 | 12 | 48 | Taobao |
| W1-4 | 65mm Mecanum wheels (upgrade) | 4 | 35 | 140 | Taobao |
| — | USB hub, UART bridge, fan, cables | lot | — | ~50 | Taobao/LCSC |
| | | | **Upgrade total** | **~¥1,520** | |

### Optional Add-ons

| Add-on | Cost (¥) | Purpose |
|:-------|:---------|:--------|
| LD06 LiDAR | 120 | 2D SLAM + Nav2 autonomous navigation |
| 4G LTE module | 168 | Remote operation, fleet telemetry |
| Rear USB camera | 65 | 360° visual coverage |
| Extra 2S battery pack | 35 | Extended runtime (~2× baseline) |

---

## Alternative Parts

If a component is unavailable, these substitutes are verified compatible:

| Original | Alternative | Notes |
|:---------|:-----------|:------|
| DRV8833 | TB6612FNG | Pin-compatible footprint; slightly higher current rating |
| BNO055 | MPU9250 + Madgwick filter | Requires software fusion (no built-in AHRS); cheaper |
| ESP32-S3-WROOM-1-N8R8 | ESP32-S3-WROOM-1-N16R8 | 16MB flash variant; same pinout |
| LD06 LiDAR | LD19 | Same protocol, 12m range (vs 8m), slightly more expensive |
| HC-SR04 | VL53L0X ToF | I2C interface (fewer GPIO); shorter range (2m vs 4m) |
| N20 1:90 motor | N20 1:100 motor | Slightly slower top speed; more torque |
| 48mm Mecanum wheel | 65mm Mecanum wheel | Better ground contact; requires bracket adjustment |
| MT3608 | SY7208 | Pin-compatible boost; wider input range |
| Raspberry Pi 5 | Orange Pi 5 Plus | RK3588 SoC; needs different HAT for Hailo |

---

## Delivery Time Estimates

| Region | Electronics (LCSC) | Mechanical (Taobao/AliExpress) | SBC + AI (Pimoroni/Hailo) |
|:-------|:------------------|:------------------------------|:--------------------------|
| China (mainland) | 1-3 days | 2-4 days | 5-10 days |
| Asia Pacific | 5-10 days | 7-15 days | 5-10 days |
| Europe | 7-14 days | 10-20 days | 3-7 days |
| North America | 7-14 days | 10-25 days | 5-10 days |
| Other | 10-20 days | 15-30 days | 7-14 days |

*Plan 3-4 weeks lead time for a complete order when sourcing internationally.*

---

## BOM File Descriptions

| File | Purpose |
|:-----|:--------|
| `bom_basic.csv` | Complete Basic SKU parts list |
| `bom_standard.csv` | Standard SKU upgrade components (add to Basic) |
| `bom_optional_addons.csv` | Optional peripherals (LiDAR, 4G, cameras) |
| `bom_industrial.csv` | Industrial-grade components (550 motors, IP54, 5G) |

CSV format: `Reference, Value, Package, Manufacturer, MPN, Quantity, Unit_Price_CNY, Supplier, Notes`

---

## Next Steps

- [Assembly Guide](../docs/assembly_guide.md) — Step-by-step build instructions
- [Getting Started (AI Researchers)](../docs/getting_started_ai.md) — Software-first path, no hardware needed
- [PCB Design](pcb/README.md) — Schematic and layout details
