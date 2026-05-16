# SPDX-License-Identifier: CERN-OHL-P-2.0
# Charging Dock — Design Specification

## Overview

The charging dock enables autonomous battery charging through physical pogo-pin
contact. The robot navigates to the dock using visual servoing on an AprilTag
marker, then makes contact via mechanical guide rails that funnel into alignment.

## Block Diagram

```
[12V DC Input] → [Polyfuse] → [TP5100 Charger IC]
                                     │
                                     ├─→ [Pogo Pin Contacts] → Robot Battery
                                     │
                                     └─→ [Current Sense R5]
                                              │
                              [ATtiny85 MCU] ←─┘
                                   │
                        ┌──────────┼──────────┐
                        │          │          │
                   [WS2812B]  [Data Pin]  [Fault Logic]
                   Status LED   to Robot    (OVP/OCP)
```

## Functional Requirements

1. **Charging**: 2S Li-ion (7.4V nominal, 8.4V max), 2A charge current
2. **Safety**: Overcurrent (polyfuse), overvoltage (TP5100 internal), reverse polarity (Schottky D1)
3. **Communication**: UART 9600 baud via data pogo pin (charge state, current, voltage)
4. **Visual**: AprilTag 36h11 (ID 0), 160mm square, at height 350mm from floor
5. **Mechanical**: V-profile guide rails for ±30mm lateral alignment tolerance
6. **Indicators**: WS2812B LEDs (green=charging, blue=ready, red=fault, purple=aligning)

## Electrical Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Input voltage | 12V ±10% | DC barrel jack or USB-C |
| Charge voltage | 8.4V (2S) | TP5100 auto-detect |
| Max charge current | 1.5A | Set by R6=1.5kΩ (reduced from 2A for thermal margin) |
| Trickle current | 100mA | Below 6.0V threshold |
| Termination current | 100mA (C/20) | Charge complete |
| Logic voltage | 3.3V | AMS1117 LDO |
| Standby power | <0.5W | No robot connected |

## Pogo Pin Pinout

| Pin | Function | Notes |
|-----|----------|-------|
| 1 | V+ (charge/sense) | 8.4V max, 2A. Voltage-divided to 0–3.3V for robot-side ADC dock detection AND charge level monitoring |
| 2 | GND | Power ground |
| 3 | DATA | UART TX/RX (3.3V logic) |
| 4 | RESERVED | Available for future use (digital detect, auxiliary data, or sense) |

### Dock Detection Method

The robot detects docking state via **analog voltage sensing** on Pin 1. A resistor
divider on the robot-side pogo pin scales the charge voltage (0–8.4V) down to the
ESP32-S3 ADC range (0–3.3V). The firmware applies a threshold (default 2.0V after
divider) to determine contact:

- **Above threshold**: Docked — charge voltage present, pogo contact confirmed
- **Below threshold**: Undocked — no charge source connected

This approach is preferred over a dedicated digital DETECT pin because:
1. It provides richer information (partial contact, charge level, connection quality)
2. It uses fewer pogo pins (Pin 4 freed for future use)
3. A digital "docked" signal is trivially derived from the analog reading

For future dock revisions requiring a separate digital detection line, the firmware
supports an optional secondary GPIO input (compile-time configurable via Kconfig
`CONFIG_ROBOT_DOCKING_DIGITAL_DETECT`). When both methods are enabled, OR-logic
applies — either method confirming contact is sufficient.

## ATtiny85 Firmware

The dock-side MCU handles:
- ADC reading of current sense (charge current monitoring)
- UART communication with robot (report charge state)
- WS2812B LED control (status visualization)
- Timeout watchdog (disconnect if no current for 60s)
- Temperature monitoring via NTC on charge MOSFET

## PCB Design Constraints

- 2-layer PCB, 1.6mm FR4
- Min trace width: 0.3mm (signal), 1.0mm (power, 2A)
- Thermal relief on TP5100 ground pad
- Pogo pin footprint: custom, 2mm pitch, 4-pin
- Keep AprilTag area clear of copper (interference with camera)
- Mounting holes: 4x M3 at corners

## Safety Compliance

- Meets IEC 62368-1 (Audio/Video/IT equipment safety)
- LVD: <60V DC
- Creepage: >1mm between high/low voltage traces
- Thermal shutdown: TP5100 internal (junction >150°C)

## TODO (Manual Steps)

- [ ] Create KiCad 8 schematic (symbol library in hardware/pcb/libs/)
- [ ] Layout PCB with pogo pin connector placement
- [ ] Generate Gerber files for manufacturing
- [ ] 3D model enclosure (FreeCAD or Fusion 360)
- [ ] Thermal analysis for 2A continuous charging
- [ ] ATtiny85 firmware (separate repo or firmware/charging_dock/)
