# SPDX-License-Identifier: CERN-OHL-P-2.0
# Charging Dock BOM (Bill of Materials)
# Status: DRAFT — awaiting schematic review

| Ref | Part | Value | Package | Qty | Notes |
|-----|------|-------|---------|-----|-------|
| U1 | TP5100 | — | SOP-8 | 1 | Dual-cell Li-ion charger IC (2A max) |
| U2 | AMS1117-3.3 | 3.3V | SOT-223 | 1 | LDO for logic supply |
| U3 | ATtiny85 | — | SOIC-8 | 1 | Dock-side MCU (LED control, current sense) |
| Q1 | AO3400 | N-CH MOSFET | SOT-23 | 1 | Charging path switch |
| D1 | SS34 | Schottky 3A | SMA | 1 | Reverse polarity protection |
| D2 | WS2812B | RGB LED | 5050 | 2 | Status indicators |
| R1-R4 | — | 10kΩ | 0402 | 4 | Pull-ups, dividers |
| R5 | — | 0.1Ω 1% | 2512 | 1 | Current sense resistor |
| R6 | — | 2.4kΩ | 0402 | 1 | TP5100 charge current set (1.0A — thermal safe at 12V input) |
| C1-C3 | — | 10µF | 0805 | 3 | Bulk decoupling |
| C4-C6 | — | 100nF | 0402 | 3 | Local decoupling |
| C7 | — | 22µF | 1206 | 1 | TP5100 output capacitor |
| J1 | Pogo pin array | 4-pin | Custom | 1 | Battery contacts (V+, V-, data, GND) |
| J2 | DC barrel jack | 5.5x2.1mm | Through-hole | 1 | 12V input power |
| J3 | USB-C | Power only | SMD | 1 | Alternate 5V input (PD not required) |
| F1 | Polyfuse | 3A | 1812 | 1 | Overcurrent protection |
| LED1 | — | Green | 0805 | 1 | Charging indicator |
| LED2 | — | Red | 0805 | 1 | Fault indicator |
| TAG1 | AprilTag 36h11 | ID 0 | Printed label | 1 | 160mm x 160mm visual marker |

## Mechanical Components

| Part | Specification | Qty | Notes |
|------|--------------|-----|-------|
| Pogo pin | Spring-loaded, 2A rated, 2mm pitch | 4 | Mill-Max 0906-x series or equiv. |
| Guide rail | Aluminum, V-profile, 200mm length | 2 | Robot alignment funnel |
| Mounting bracket | Steel, L-bracket, M4 holes | 2 | Wall mount |
| Enclosure | ABS, IP40, 400x300x150mm | 1 | 3D-printed or injection molded |

## Power Budget

| Rail | Voltage | Max Current | Source |
|------|---------|-------------|--------|
| Input | 12V DC | 3A | Barrel jack / USB-C PD |
| Charge | 8.4V | 1.0A | TP5100 output |
| Logic | 3.3V | 50mA | AMS1117 |

## Design Notes

- TP5100 configured for 2S (8.4V) charging at 1.0A (R6=2.4kΩ)
- Thermal dissipation at 12V input: (12-8.4)×1.0 = 3.6W — requires 1.5cm² copper pour minimum
- For cooler operation, prefer 9V USB-C PD input: (9-8.4)×1.0 = 0.6W (cool, no heatsink needed)
- Charge time with 3000mAh pack: ~3 hours (acceptable for overnight/between-task charging)
- Current sense on low-side (R5) feeds ATtiny85 ADC for charge monitoring
- Dock communicates charge status to robot via pogo pin data line (UART 9600)
- AprilTag ID 0 is reserved for the primary docking station
- PCB to be designed in KiCad 8+ (TODO: create schematic)
