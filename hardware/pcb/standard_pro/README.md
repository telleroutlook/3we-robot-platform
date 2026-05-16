# Standard-Pro SKU — Motor Driver & Encoder Upgrade

> SPDX-License-Identifier: CERN-OHL-P-2.0

## Overview

The Standard-Pro variant replaces the desktop-class N20 + DRV8833 drivetrain with
a higher-torque JGA25-370 + TB6612FNG combination, enabling operation on carpet,
outdoor surfaces, and payloads exceeding 800 g total system weight.

## Key Specifications

| Parameter | Standard (current) | Pro (this SKU) |
|-----------|--------------------|----------------|
| Motor | N20 micro gear motor | JGA25-370 (12V, 1:34) |
| Driver IC | DRV8833 (1.5A peak) | TB6612FNG (3.2A peak / 1.2A continuous) |
| Encoder | Magnetic, ~12 CPR | Hall effect, 11 PPR × 34 = 374 CPR |
| Wheel | 48mm Mecanum | 80mm Mecanum |
| Max payload | ~200g | ~600g |
| Power supply | 7.4V 2S LiPo | 11.1V 3S LiPo (12V rail via buck) |

## Firmware Compatibility

The ESP32-S3 firmware uses the **PCNT hardware peripheral** for encoder counting
(`encoder_init()` in `motor_control.c`). This is critical for the Pro SKU:

- JGA25 Hall encoder pulse frequency: 374 CPR × (530 RPM / 60) ≈ 3,300 Hz per wheel
- Four wheels total: ~13.2 kHz aggregate pulse rate
- GPIO interrupt approach would consume excessive CPU — PCNT handles this in hardware

No firmware code changes are required; only the PCNT pulse-per-revolution constant
needs updating in `config/motor_params.h`:

```c
#define ENCODER_CPR 374  // Was 12 for N20
```

## PCB Changes from Standard

1. **Motor driver footprint**: SSOP-24 (TB6612FNG) replaces WSON-10 (DRV8833)
2. **Motor connector**: JST-PH 6-pin (2× power + 2× Hall A/B + VCC + GND) × 4
3. **Power input**: XT60 connector, 3S-rated capacitors (25V electrolytic)
4. **Current sense**: 0.1Ω shunt resistors on each motor H-bridge low-side
5. **Buck converter**: MP2315 (or equivalent) for 5V/3A logic rail from 12V input

## BOM Additions (per unit, approximate)

| Component | Qty | Est. Cost |
|-----------|-----|-----------|
| TB6612FNG | 2 | $3.00 |
| JGA25-370 w/ encoder | 4 | $28.00 |
| 80mm Mecanum wheel set | 1 | $25.00 |
| 3S 2200mAh LiPo | 1 | $18.00 |
| XT60 connector pair | 1 | $1.00 |
| MP2315 buck module | 1 | $2.50 |
| 0.1Ω 1W shunt resistors | 4 | $0.40 |
| **Total delta vs Standard** | | **~$78** |

## File Structure (planned)

```
standard_pro/
├── README.md              ← this file
├── standard_pro.kicad_pro ← KiCad 8 project (placeholder)
├── standard_pro.kicad_sch ← schematic (placeholder)
├── standard_pro.kicad_pcb ← PCB layout (placeholder)
└── bom.csv                ← bill of materials
```

## Status

**Backlog** — This is a hardware-only change that does not block any software
deliverables. The software stack (SDK, Gym environments, ROS2 nodes) is already
parameterized for arbitrary encoder CPR and motor characteristics.

## Design Decisions

- TB6612FNG chosen over L298N: much smaller, no heat sink required at 1.2A continuous
- 80mm wheels chosen for ground clearance on uneven surfaces
- Hall encoders (not optical) for dust/debris resilience in outdoor use
- Current sense shunts enable per-motor current monitoring via ADC, feeding
  `get_motor_current()` API for Sim2Real domain randomization research
