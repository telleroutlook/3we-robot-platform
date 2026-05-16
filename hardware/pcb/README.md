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
Battery Pack(s) ─── XT30 ──→ Q8 P-MOS ──→ VBAT Bus (7.4V)
                              (reverse      │
                              protection)   │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
                    ▼                          ▼                      ▼
              MP2359 Buck              MP1584EN Buck            [Safety Relay]
              5V / 1.2A                5V / 5A                       │
              (ESP32, sensors)              │                    Coil supply:
                    │               ┌──────┼──────┐           +5V_ESP → SW1b NC
                    ▼               │      │      │           → +5V_ESTOP_COIL
              AP2112K-3.3        Q6a/Q6b   Q3                 → RLY1 coil
              3.3V / 600mA       P-MOS SW  P-MOS SW                  │
              (logic, I2C)          │         │                      ▼
                                    ▼         ▼               Motor DRV8833
                              +5V_PI_SW   +5V_PAYLOAD         (7.4V / 10A max)
                              (Pi5, 3A)   (Payload, 2A)
                              GPIO45 ctrl  MCP23017 ctrl
```

### Supervisory Circuits

- **TPS3813 (U10)**: External watchdog, 1.6s timeout. GPIO46 toggles WDI; if firmware
  hangs, RST pulls ESP32 EN low → hardware reset. Independent of software watchdog.
- **Pi5 Power Switch (Q6a/Q6b/Q7)**: Dual Si2301CDS P-MOS (parallel, 5A total) with
  AO3400A N-MOS driver. GPIO45 HIGH = Pi5 ON. Default OFF at boot (R34 pull-down).
  Standard/Industrial SKU only (DNP on Basic).
- **E-stop Safety Path (SW1b → RLY1)**: The E-stop button has dual NC contact pairs.
  NC2 (SW1b) is in series with the safety relay coil +5V supply. Pressing E-stop
  physically breaks the coil circuit → relay de-energizes → motor power cut. This is
  a pure hardware interlock — zero firmware dependency, compliant with ISO 13850.
  R17 (Q5 gate pull-up) also connects to +5V_ESTOP_COIL so the N-MOS driver loses
  gate drive simultaneously.

## PBC-34 Payload Bus Connector

2×17 pin header (2.54mm pitch), keyed with polarization notch.

| Pin | Function | Rating | Notes |
|-----|----------|--------|-------|
| 1-2 | +5V Power | 3A max | P-MOS soft-start, switched from +5V_PI (MP1584EN 5A rail) via MCP23017 GPA0 |
| 3-4 | +12V Power | 3A max | MOSFET soft-start |
| 5-6 | GND (Power) | — | Wide traces (1mm) |
| 7 | I2C SDA | 3.3V | Direct (shared bus with IMU, INA219, MCP23017) |
| 8 | I2C SCL | 3.3V | Direct (shared bus with IMU, INA219, MCP23017) |
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
- BNO055 IMU: 100nF + 10µF bulk cap on VDD (C4 + C17, per datasheet)

## MCP23017 Interrupt (TP1)

INTA is active-low open-drain with 10k pull-up (R36), routed to test pad TP1.
Mirror mode combines both ports onto INTA. Current firmware uses 100ms polling.

To enable interrupt-driven operation (future rev or user modification):
1. Bridge TP1 to an available ESP32 GPIO via bodge wire
2. Configure GPIO as input with pull-up, falling-edge interrupt
3. In ISR: read MCP23017 INTCAP register to identify source (payload detect,
   DRV8833 fault, GPIO change)
4. Reduces I2C bus load from continuous polling to event-driven

## Status Display Panel (Optional Add-on)

1.3" SH1106 128×64 OLED with 3 integrated tactile buttons (UP/DOWN/OK).
Connects via existing I2C bus (address 0x3C) + MCP23017 button inputs.

| Signal | Connection | Notes |
|--------|-----------|-------|
| OLED VCC | +3V3 | From I2C header |
| OLED GND | GND | From I2C header |
| OLED SDA | I2C_SDA (GPIO 1) | Shared bus |
| OLED SCL | I2C_SCL (GPIO 2) | Shared bus |
| BTN_UP | MCP23017 GPB6 | Active-low with internal pull-up |
| BTN_DOWN | MCP23017 GPB7 | Active-low with internal pull-up |
| BTN_OK | MCP23017 GPA4 | Active-low with internal pull-up |

No PCB modification required. Module mounts on chassis top panel via M2 standoffs,
connects through 4-pin GH1.25 (I2C) + 3-pin GH1.25 (buttons) to mainboard headers.

I2C bus load: +10pF capacitance (SH1106 typical). Existing 2.2kΩ pull-ups remain
adequate for 400kHz with total bus capacitance < 250pF.

## Industrial SKU Motor Driver Strategy

The mainboard PCB uses DRV8833 (dual H-bridge, 1.2A/ch) for Basic and Standard SKUs. The Industrial SKU requires BTS7960 (43A half-bridge) for 550 motors at 12V.

### Approach A: External Module (Initial Batch)

#### CAN Bus Termination (R9, 120Ω)

R9 is a 120Ω CAN bus termination resistor, **shipped as DNP (Do Not Populate)** on
Basic and Standard SKUs (which have no CAN bus).

**For Industrial SKU:** R9 MUST be populated (soldered) when:
- The robot is at one end of the CAN bus (most single-robot setups)
- The Payload device does NOT provide its own termination

**Do NOT populate R9 when:**
- The robot sits in the middle of a multi-node CAN chain
- Both ends of the bus are already terminated by other nodes

CAN bus requires exactly two 120Ω terminations — one at each physical end of the
bus. Measure 60Ω between CAN-H and CAN-L (bus powered off) to confirm correct
termination.

Recommended for first production run (< 100 units):

- Mainboard PCB unchanged — no BTS7960 footprint on-board
- Motor power output via 4× XT30 connectors (2-pin, 30A rated)
- PWM/EN signals routed to GH1.25-4P connector (PWM_H, PWM_L, VCC, GND)
- Off-the-shelf BTS7960 module (¥18/ea, 2 modules for 4 motors)
- Mounting: M3 standoffs on chassis plate, 100mm motor wires

Advantages: No PCB re-spin, fast iteration, replaceable if damaged.

### Approach B: Integrated PCB (Volume Production)

For production run > 500 units:

- New KiCad variant: `robot-platform-industrial.kicad_pcb`
- Replace DRV8833 area with 4× BTS7960 half-bridge ICs
- Add ACS712-05B current sense on each motor phase
- Requires: larger board (140×100mm), heatsink mounting holes, thermal vias under driver pads
- Internal ground plane extended for thermal relief
- Estimated NRE: ¥3,000 (4-layer prototype + stencil)

### Decision Criteria

| Factor | Approach A | Approach B |
|--------|-----------|-----------|
| Unit cost (motor driver) | ¥36 (2 modules) | ¥24 (bare ICs + passives) |
| PCB NRE | ¥0 | ¥3,000 |
| Break-even | — | ~250 units |
| Assembly complexity | Higher (wiring) | Lower (SMT) |
| Reliability | Module connectors | Soldered joints |
| Thermal management | Module heatsink | PCB thermal vias + external heatsink |

**Current decision**: Approach A for initial batch (Q2 2026). Evaluate Approach B after 100-unit production feedback.

## Manufacturing Notes

- Gerber format: RS-274X
- Drill file: Excellon format
- Pick and place: centroid + rotation per component
- All resistors/capacitors 0402 minimum (0603 preferred for hand assembly)
- QFN packages require solder paste stencil (0.12mm thickness)
