# PCB Design Documentation

## Overview

The robot-platform mainboard integrates the ESP32-S3 MCU, motor drivers, power management, sensor interfaces, and the PBC-34 payload connector on a single 4-layer PCB.

## Board Specifications

| Parameter | Value |
|-----------|-------|
| Dimensions | 120 × 90 mm |
| Layers | 4 (Signal - GND - Power - Signal) |
| Minimum trace width | 0.15 mm |
| Minimum via | 0.3 mm drill / 0.6 mm pad |
| Clearance | 0.2 mm |
| Copper weight | 1 oz (outer), 1 oz (inner) |
| Surface finish | ENIG (lead-free) |
| Board thickness | 1.6 mm |

## Layer Stack

| Layer | Usage |
|-------|-------|
| Top | Signal traces, component pads |
| Inner 1 | Ground plane (unbroken) |
| Inner 2 | Power distribution (VBAT, 5V, 3.3V, 12V) |
| Bottom | Signal traces, component pads |

## Power Architecture

```
Battery Pack(s) ─── XT30 ──→ P-MOS OR ──→ VBAT Bus (7.4V)
                                              │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
                    ▼                          ▼                      ▼
              MT3608 Boost              MP1584EN Buck            [Safety Relay]
              5V / 2A                   5V / 5A (Pi5)                 │
              (ESP32, sensors)          (compute)                     ▼
                    │                                           Motor DRV8833
                    ▼                                           (7.4V / 10A max)
              AMS1117-3.3
              3.3V / 800mA
              (logic, I2C)
```

## PBC-34 Payload Bus Connector

2×17 pin header (2.54mm pitch), keyed with polarization notch.

| Pin | Function | Rating | Notes |
|-----|----------|--------|-------|
| 1-2 | +5V Power | 3A max | MOSFET soft-start, TPS5430 supply (Standard+ SKU) |
| 3-4 | +12V Power | 3A max | MOSFET soft-start |
| 5-6 | GND (Power) | — | Wide traces (1mm) |
| 7 | I2C SDA | 3.3V | Via PCA9546 mux |
| 8 | I2C SCL | 3.3V | Via PCA9546 mux |
| 9 | UART TX | 3.3V | From payload to platform |
| 10 | UART RX | 3.3V | From platform to payload |
| 11-18 | GPIO ×8 | 3.3V | Via MCP23017 expander |
| 19 | USB D+ | — | Hub downstream port |
| 20 | USB D- | — | Hub downstream port |
| 21 | CAN-H | — | Industrial SKU only |
| 22 | CAN-L | — | Industrial SKU only |
| 23-24 | VBAT Direct | 10A | PPTC protected |
| 25 | ENABLE | Active low | Power control |
| 26 | FAULT | Open drain | Payload fault |
| 27 | DETECT | Mechanical | Spring contact |
| 28 | INT | Active low | Interrupt request |
| 29 | +3.3V Ref | 100mA | Logic reference |
| 30 | ID SCL | — | EEPROM discovery |
| 31 | ID SDA | — | EEPROM discovery |
| 32-34 | GND (Signal) | — | Signal return |

## ESD Protection

- TVS diodes on all external-facing pins (PBC-34, USB, motor connectors)
- ESD rating: IEC 61000-4-2, ±8kV contact / ±15kV air
- Specific parts: PESD5V0S1BB (single-line) on signal pins

## Design Rules

- Power traces: 2mm minimum for motor current paths
- Keep analog (ADC, encoder) traces away from PWM/motor traces
- Ground plane stitching vias every 5mm along board edges
- Motor driver thermal pads connected to internal ground plane
- Decoupling capacitors placed within 3mm of IC power pins
- USB differential pairs: 90Ω impedance controlled

## Manufacturing Notes

- Gerber format: RS-274X
- Drill file: Excellon format
- Pick and place: centroid + rotation per component
- All resistors/capacitors 0402 minimum (0603 preferred for hand assembly)
- QFN packages require solder paste stencil (0.12mm thickness)
