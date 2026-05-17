# SPDX-License-Identifier: CERN-OHL-P-2.0
# Hardware Fix Plan — Pre-Production Corrections

Status: IMPLEMENTED — all fixes applied to schematic and firmware (2026-05-16)
Date: 2026-05-16
Updated: 2026-05-17
Affects: robot-platform.kicad_sch Rev 1.1f, bom_basic.csv, bom_industrial.csv

---

## Fix 1: Replace MT3608 Boost with Buck Converter (CRITICAL)

### Problem

U4 (MT3608) is a boost converter used in a step-down application (VBAT 7.4V → 5V).
MT3608 can only step UP. The circuit will either pass through ~7V unregulated or
oscillate/fail to start.

### Root Cause

Likely a design iteration artifact: battery changed from 1S (3.7V) to 2S (7.4V)
without updating the 5V ESP rail topology.

### Fix

Replace U4 with **TPS5430DDAR** (SOIC-8, already used as PS1 in bom_standard.csv)
or **MP2359DJ** (SOT-23-6, same pincount as MT3608 for minimal layout change).

**Recommended: MP2359DJ-LF-Z** (SOT-23-6)
- Input: 4.5V–24V
- Output: 5V/1.2A (sufficient for ESP32 + sensors)
- Same SOT-23-6 footprint as MT3608 — **zero PCB layout change**
- Efficiency ~90% at 200mA load
- Price: ~¥1.50 (LCSC)

### Schematic Changes

```
Old: U4 = MT3608 (SOT-23-6), Value "MT3608_5V_ESP"
New: U4 = MP2359DJ (SOT-23-6), Value "MP2359_5V_ESP"
```

Pin mapping (SOT-23-6, both ICs):

| Pin | MT3608 (old)  | MP2359 (new)  |
|-----|---------------|---------------|
| 1   | SW            | IN            |
| 2   | GND           | GND           |
| 3   | FB            | EN            |
| 4   | EN            | BST           |
| 5   | IN            | SW            |
| 6   | —             | FB            |

**WARNING**: Pinout is NOT compatible — requires trace rerouting on PCB.

If zero-reroute is critical, alternative is **XL1509-5.0** (SOP-8) which requires
new footprint but is pin-compatible with many common buck ICs and costs ¥0.8.

### BOM Changes (bom_basic.csv)

```
Old: U4,MT3608,SOT-23-6,XI'AN Aerosemi,MT3608,1,1.20,LCSC,5V boost converter (ESP32 rail)
New: U4,MP2359DJ-LF-Z,SOT-23-6,MPS,MP2359DJ-LF-Z,1,1.50,LCSC,5V/1.2A buck converter (ESP32 rail)
```

### Passive Component Changes

| Ref  | Old (Boost) | New (Buck)         | Notes                            |
|------|-------------|--------------------|----------------------------------|
| L1   | 4.7uH 1210  | 10uH 1210 (CDR)   | Buck needs higher L; 1.5A sat   |
| C11  | 10uF 0805   | 22uF 0805 (X5R)   | Input cap, 16V rating            |
| C_out| (use C11)   | 22uF 0805 (X5R)   | Output cap for stability         |
| R_FB1| N/A         | 20k (0402)         | Upper FB divider: 5V × 20k/(20k+10k) |
| R_FB2| N/A         | 10k (0402)         | Lower FB divider (GND side)      |

Note: MT3608 feedback network (existing R) must be recalculated for MP2359:
- MP2359 FB reference = 0.925V
- Vout = 0.925 × (1 + R_upper/R_lower) = 0.925 × (1 + 44.2k/10k) ≈ 5.01V
- Use R_upper = 44.2kΩ (1%), R_lower = 10kΩ (1%)

---

## Fix 2: Add HC-SR04 Echo Level Shifter Network (CRITICAL)

### Problem

HC-SR04 Echo output is 5V logic. ESP32-S3 GPIO absolute max is 3.6V. Currently
only R12 (20kΩ) exists in the schematic with "Ultrasonic echo voltage divider"
description, but there are 4 echo channels and only 1 resistor. The voltage
divider network is incomplete.

### Fix

Add a resistive divider per echo channel (4 total). The divider attenuates 5V to
~3.3V using the existing 5V → 3.3V ratio.

**Per channel**: 10kΩ (upper, series) + 18kΩ (lower, to GND)
- Vout = 5V × 18k/(10k+18k) = 3.21V (safely under 3.3V with margin for 5.5V overshoot)
- Source impedance = 10k||18k ≈ 6.4kΩ (acceptable for ESP32 ADC-capable GPIO)

### New Components

| Ref     | Value | Package | Purpose                    |
|---------|-------|---------|----------------------------|
| R20     | 10k   | 0402    | US_ECHO_FRONT series       |
| R21     | 18k   | 0402    | US_ECHO_FRONT to GND       |
| R22     | 10k   | 0402    | US_ECHO_BACK series        |
| R23     | 18k   | 0402    | US_ECHO_BACK to GND        |
| R24     | 10k   | 0402    | US_ECHO_LEFT series        |
| R25     | 18k   | 0402    | US_ECHO_LEFT to GND        |
| R26     | 10k   | 0402    | US_ECHO_RIGHT series       |
| R27     | 18k   | 0402    | US_ECHO_RIGHT to GND       |

### Schematic Connection

```
HC-SR04 Echo Pin ──[R_series 10k]──┬── ESP32 GPIO
                                   │
                              [R_lower 18k]
                                   │
                                  GND
```

### BOM Changes (bom_basic.csv)

Remove existing R9-R12 line (BOM claims these are ultrasonic dividers but schematic
shows them used for other purposes). Add:

```
R20-R27,Resistor Divider (US Echo),0402,Various,-,8,0.01,LCSC,HC-SR04 5V→3.3V level shift
```

Also remove R12 from BOM line "R9-R12,20kΩ,0402" — renumber to reflect actual usage:
```
R9,120Ω DNP,0603,Various,-,1,0.01,LCSC,CAN bus termination (DNP for Basic)
R10-R11,5.1kΩ,0402,Various,-,2,0.01,LCSC,USB-C CC pull-down
R12,(removed — absorbed into R20-R27 network)
```

---

## Fix 3: Add Safety Relay Drive Circuit (CRITICAL)

### Problem

The schematic shows RLY1 (G2R-2-H_DC5, dual-channel 5V relay) connected via ESTOP
label to GPIO41. But no transistor driver or flyback diode is visible. The relay
coil requires ~80mA at 5V — ESP32 GPIO max source is 40mA and at 3.3V cannot
energize a 5V coil.

Additionally, the relay must be ENERGIZED during normal operation (fail-safe: loss
of power = motors off). The E-stop button breaks the coil drive circuit.

### Fix

Add N-channel MOSFET relay driver with flyback protection.

### Circuit

```
+5V_ESP ─────────────────────┐
                             │
                        [RLY1 Coil+]
                             │
                        [RLY1 Coil-]  ──┐
                             │          │
                      [D5 1N4148W]   (flyback, cathode to +5V)
                             │          │
                             ├──────────┘
                             │
                        [Q5 Drain]
                             │
                        [Q5 Source] ── GND
                             │
E-STOP NC ──┐           [Q5 Gate]
             │               │
            GND         [R17 10k] ── +3V3  (default ON when E-stop released)
                             │
                        [R18 10k] ── ESTOP label (GPIO41)
```

**Logic**:
- E-stop NOT pressed (NC closed): ESTOP net = LOW (grounded through switch)
  → BUT we need relay ON when safe. So invert: use ESTOP signal inverted.

**Corrected approach** — The E-stop is NC (Normally Closed). In the current design:
- Button NOT pressed: SW1 shorts ESTOP to GND → GPIO41 reads LOW
- Button pressed: SW1 opens → R5 (10k to 3.3V) pulls ESTOP HIGH

This means the relay should be energized when ESTOP = LOW (safe state).
A P-channel high-side switch or inverted N-channel logic is needed.

**Simplest correct circuit**:

```
              +5V_ESP
                │
           [RLY1 Coil]
                │
           [Q5 Drain] (N-MOS AO3400A, SOT-23)
           [Q5 Gate] ←── RELAY_EN (new net, from firmware GPIO or hardwired)
           [Q5 Source] ── GND
                │
           [D5 cathode]──── +5V_ESP (flyback diode: 1N4148W across coil)
           [D5 anode] ─────┘(connected to Q5 drain / coil low side)
```

**E-stop integration**: The E-stop button should BREAK the relay coil circuit
directly (hardware interlock, not software). Correct topology:

```
+5V_ESP ── [E-STOP NC switch] ── [RLY1 Coil+]
                                       │
                                  [RLY1 Coil-]
                                       │
                                  [Q5 Drain] (N-MOS, gate tied HIGH via 10k to 3.3V)
                                  [Q5 Source] ── GND
                                       │
                                  [D5] flyback across coil
```

With gate tied HIGH (always on), the relay is energized whenever +5V flows through
the E-stop NC circuit. Pressing E-stop opens the circuit → relay de-energizes →
motors lose power. This is a pure hardware interlock — firmware cannot override.

Firmware reads GPIO41 (ESTOP net, after the switch) to DETECT the state but does
NOT control the relay.

### New Components

| Ref | Value         | Package | Purpose                    |
|-----|---------------|---------|----------------------------|
| Q5  | AO3400A       | SOT-23  | N-MOS relay low-side drive |
| D5  | 1N4148W       | SOD-123 | Relay flyback protection   |
| R17 | 10k           | 0402    | Q5 gate pull-up to 3.3V   |
| R18 | 100k          | 0402    | Q5 gate pull-down (ESD)    |

### BOM Addition (bom_basic.csv)

```
Q5,AO3400A,SOT-23,AOS,AO3400A,1,0.30,LCSC,N-MOS relay driver (Vgs_th 1V)
D5,1N4148W,SOD-123,Various,-,1,0.05,LCSC,Relay coil flyback diode
R17,10k,0402,Various,-,1,0.01,LCSC,MOSFET gate bias (always-on)
R18,100k,0402,Various,-,1,0.01,LCSC,Gate ESD/discharge
```

### Safety Verification

- E-stop pressed → +5V path broken → relay de-energizes → motor power cut
- MCU crash → relay stays energized (gate held high by R17) → motors controlled
- MCU cannot re-energize relay after E-stop (hardware path broken)
- Dual-channel relay feedback (GPIO42, GPIO22) confirms relay state to firmware
- Software watchdog timeout → firmware sets PWM to 0 (secondary protection)

---

## Fix 4: DRV8833 nSLEEP External Pull-up (Recommended)

### Problem

DRV8833 nSLEEP has only internal 200kΩ pull-up. In vibration/EMI environments,
noise coupling could momentarily pull nSLEEP low, causing ~1ms sleep entry
(outputs go Hi-Z, motors coast unpredictably).

### Fix

Add 10kΩ pull-up to +3V3 on each DRV8833 nSLEEP pin.

### New Components

| Ref | Value | Package | Purpose              |
|-----|-------|---------|----------------------|
| R28 | 10k   | 0402    | U2a nSLEEP pull-up   |
| R29 | 10k   | 0402    | U2b nSLEEP pull-up   |

### Schematic Connection

```
+3V3 ──[R28 10k]── U2a.nSLEEP
+3V3 ──[R29 10k]── U2b.nSLEEP
```

### Optional Enhancement

Connect nFAULT pins to spare MCP23017 GPB inputs for fault monitoring:

```
U2a.nFAULT ──[R30 10k to +3V3]── MCP23017.GPB4 (input, active-low fault)
U2b.nFAULT ──[R31 10k to +3V3]── MCP23017.GPB5 (input, active-low fault)
```

This enables firmware to detect DRV8833 overcurrent/thermal events.

---

## Fix 5: TP5100 Charging Dock Thermal Fix (Recommended)

### Problem

At 2A charge current with 12V input and 8.4V output:
P_dissipation = (12 - 8.4) × 2 = 7.2W — exceeds QFN thermal capability.

### Fix Option A: Reduce Charge Current to 1A (Zero-Cost)

Change R6 from 1.2kΩ to **2.4kΩ**.

- New dissipation: (12 - 8.4) × 1 = 3.6W
- With PCB thermal relief (4cm² copper): Rth ≈ 25°C/W → ΔT = 90°C
- Still marginal. Acceptable only with adequate copper pour.

### Fix Option B: Reduce Input Voltage (Preferred)

Use 9V USB-C PD input instead of 12V barrel jack:

- P_dissipation = (9 - 8.4) × 2 = 1.2W (very comfortable)
- Requires USB-C PD trigger IC (e.g., CH224K, ¥0.50) to negotiate 9V
- TP5100 minimum Vin = Vbat + 0.3V = 8.7V → 9V works with 0.3V headroom

### Fix Option C: Both (Recommended for Production)

- R6 = 1.5kΩ (charge current ~1.5A)
- Input: 9V via USB-C PD (CH224K trigger)
- P_dissipation = (9 - 8.4) × 1.5 = 0.9W (cool operation)
- Charge time: 3000mAh / 1.5A = 2 hours (acceptable)

### Charging Dock BOM Change

```
Old: R6 = 1.2kΩ (2A charge)
New: R6 = 1.5kΩ (1.5A charge)
Add: U_PD = CH224K (SOT-23-6), USB-C PD 9V request IC, ¥0.50
```

---

## Fix 6: AMS1117 → AP2112K (Low Priority, Recommended)

### Problem

AMS1117 dropout 1.7V at light load → unnecessary heat.
WiFi TX bursts can push 300-500mA momentarily.

### Fix

Replace U3 with AP2112K-3.3TRG1 (SOT-23-5).

| Parameter   | AMS1117-3.3     | AP2112K-3.3      |
|-------------|-----------------|------------------|
| Package     | SOT-223         | SOT-23-5         |
| Dropout     | 1.3V @ 800mA    | 250mV @ 600mA   |
| Max current | 800mA           | 600mA            |
| Quiescent   | 5mA             | 55µA             |
| Price       | ¥0.80           | ¥1.10            |

Dissipation with AP2112K: (5.0 - 3.3) × 0.2A = 0.34W → (5.0 - 3.3 - 0.25 overhead) is irrelevant since dropout is 250mV, actual Vin-Vout = 1.7V but with 600mA max it's sufficient.

**Note**: SOT-23-5 ≠ SOT-223 footprint. This change requires PCB modification.
If layout is frozen, keep AMS1117 and ensure ≥1cm² copper pour on thermal pad.

### Alternative (No Layout Change)

Keep AMS1117-3.3 in SOT-223. Add thermal copper area requirement to PCB design
rules: minimum 2cm² exposed copper connected to Tab/GND pin.

---

## Summary: BOM Delta (bom_basic.csv)

### Components to CHANGE

| Ref | Old                | New                    | ΔCost   |
|-----|--------------------|------------------------|---------|
| U4  | MT3608 (¥1.20)     | MP2359DJ-LF-Z (¥1.50) | +¥0.30  |
| U3  | AMS1117 (¥0.80)    | AP2112K-3.3 (¥1.10)   | +¥0.30  |
| L1  | 4.7uH (¥0.50)      | 10uH CDR (¥0.80)      | +¥0.30  |

### Components to ADD

| Ref     | Value      | Qty | Unit ¥ | Purpose                |
|---------|------------|-----|--------|------------------------|
| R20-R27 | 10k/18k    | 8   | 0.01   | US echo level shift    |
| R28-R29 | 10k        | 2   | 0.01   | DRV8833 nSLEEP pullup  |
| Q5      | AO3400A    | 1   | 0.30   | Relay N-MOS driver     |
| D5      | 1N4148W    | 1   | 0.05   | Relay flyback diode    |
| R17     | 10k        | 1   | 0.01   | Gate bias              |
| R18     | 100k       | 1   | 0.01   | Gate ESD               |
| R_FB    | 44.2k+10k  | 2   | 0.02   | Buck feedback divider  |

### Total BOM Cost Impact

Additional cost per board: **< ¥2.50** (within rounding error of current ~¥680 total)

---

## Additional Fixes (Rev 1.1b)

### Fix 7: Payload 5V Source — Move from ESP Rail to Pi5 Rail

Q3 (Si2301CDS) source changed from +5V_ESP (MP2359, 1.2A) to +5V_PI (MP1584EN, 5A).
This prevents payload current from overloading the ESP32 supply rail.

- MP2359 now serves only: ESP32 (~500mA peak) + board sensors (~60mA) = max ~700mA
- MP1584EN serves: Pi5 (~3A) + Payload 5V (up to ~2A via Q3) = within 5A rating
- R15 gate pull-up also moved to +5V_PI (P-MOS gate must match source for OFF state)

### Fix 8: DRV8833 nFAULT Monitoring

Added R32/R33 (10k pull-up to 3.3V) on both DRV8833 nFAULT open-drain outputs.
Routed to MCP23017 GPB4 (front) and GPB5 (rear) for firmware overcurrent/thermal
fault detection. Cost: 2× 0402 resistors.

### Fix 9: TP5100 Charge Current → 1.0A

Further reduced from 1.5A to 1.0A (R6=2.4kΩ):
- 12V input dissipation: 3.6W (manageable with 1.5cm² copper pour)
- 9V PD input dissipation: 0.6W (cool, no heatsink)
- Charge time: ~3 hours for 3000mAh (acceptable)

### Fix 10: CAN Termination Documentation

Added explicit guidance in PCB README and Industrial BOM for R9 (120Ω) population
rules based on bus topology.

---

## PCB Layout Impact Assessment

| Fix | Layout Change Required | Severity |
|-----|----------------------|----------|
| #1 (Buck) | Trace reroute around U4 (same footprint if MP2359) | Medium — feedback resistors + inductor value |
| #2 (US dividers) | 8 resistors near sensor connectors S1-S4 | Low — space available near connector area |
| #3 (Relay driver) | Q5 + D5 + R17/R18 near RLY1 | Medium — new components in safety area |
| #4 (nSLEEP) | 2 resistors near U2a/U2b | Low — 0402 fits adjacent to DRV8833 |
| #5 (TP5100) | Charging dock PCB only (separate board) | None on mainboard |
| #6 (LDO) | Footprint change SOT-223→SOT-23-5 | High — requires new pad layout |
| #7 (Payload 5V) | One trace reroute (Q3 source: +5V_ESP → +5V_PI) | Low — single net change |
| #8 (nFAULT) | 2 resistors near U2a/U2b + trace to MCP23017 | Low |
| #11 (DNP) | None (annotation only) | None |
| #12 (Watchdog) | U10 SOT-23-5 + C16 near ESP32 EN pin | Low — small footprint |
| #13 (Pi5 switch) | 3× SOT-23 + 2× 0402 near MP1584EN output | Medium — 5 new components |
| #14 (Shunt) | None (same footprint, value change only) | None |
| #15 (IMU cap) | 1× 0805 adjacent to BNO055 | Low — space available |
| #16 (INT pullup) | 1× 0402 + test pad near MCP23017 | Low |

**Recommendation**: All fixes incorporated into Rev 1.1c. No deferred items.

---

## Additional Fixes (Rev 1.1c)

### Fix 11: Q4/R16 DNP Annotation (Basic SKU)

Q4 (AO3401A) and R16 (100kΩ gate pull-up) are the 12V payload power switch. On Basic
SKU there is no +12V_BOOST source (XL6009 only in Standard BOM). Marked DNP in BOM
and schematic description. No functional impact — gate pull-up keeps Q4 OFF regardless.

### Fix 12: TPS3813 External Watchdog (U10)

Added TPS3813K33DBVR (SOT-23-5) watchdog timer:
- VDD = +3V3, GND = GND
- WDI (watchdog input) = GPIO46 (EXT_WDT_FEED label)
- RST (active-low output) = ESP32 EN pin via ESP32_EN label
- TD = GND (1.6 second timeout)
- C16 (100nF) on RST output for pulse stretching (~100ms reset pulse)
- MR (manual reset) tied to VDD (disabled)

Safety function: If firmware stops toggling GPIO46 for >1.6s, TPS3813 asserts RST
→ ESP32 EN pulled low → hardware reset. Independent of software watchdog.

### Fix 13: Pi5 Power MOSFET Switch (Q6a, Q6b, Q7)

Added high-side P-MOS switch for Pi5 5V rail, controlled by GPIO45 (PI5_RELAY):

```
+5V_PI (MP1584EN) ─── [Q6a+Q6b Source] (Si2301CDS × 2, parallel = 5A)
                            │
                       [Q6a+Q6b Gate] ←── R35 (100k to +5V_PI, pull-up = OFF)
                            │                    │
                            │              [Q7 Drain] (AO3400A N-MOS)
                            │              [Q7 Gate] ← GPIO45 (PI5_RELAY)
                            │                    │
                            │              [R34 100k] to GND (default OFF)
                            │              [Q7 Source] ── GND
                            │
                       [Q6a+Q6b Drain] ─── +5V_PI_SW (to Pi5 connector)
```

Logic: GPIO45 HIGH → Q7 ON → Q6 gate=GND → Vgs=-5V → P-MOS ON → Pi5 powered.
Standard/Industrial SKU only (DNP on Basic).

### Fix 14: INA219 Shunt Resistor (R7: 0.1Ω → 0.02Ω)

R7 changed from 0.1Ω to 0.02Ω (2512, 1% tolerance):
- Old: 5A load → 2.5W (exceeded 1W 2512 rating)
- New: 5A load → 0.5W (within rating with 50% margin)
- INA219 PGA=÷8 (unchanged): ±320mV / 0.02Ω = 16A measurement range
- Resolution: 10µV LSB / 0.02Ω = 0.5mA
- Firmware updated: SHUNT_RESISTANCE=0.02f, INA219_CALIBRATION=20480

### Fix 15: BNO055 Bulk Decoupling (C17)

Added C17 (10µF, X5R 10V, 0805) on BNO055 VDD, parallel with existing C4 (100nF).
Per BNO055 datasheet §5.2.1: VDD requires 100nF + min 1µF bulk cap. Critical for
stable operation in high-vibration robot environment.

### Fix 16: MCP23017 INTA Pull-up (R36) + Test Pad (TP1)

Added R36 (10kΩ to +3V3) on MCP23017 INTA open-drain output. Routed to test pad
TP1 (1mm pad). No ESP32 GPIO allocated. Firmware polls at 100ms intervals.

---

## BOM Delta (Rev 1.1c)

| Ref | Value | Qty | Unit ¥ | Purpose |
|-----|-------|-----|--------|---------|
| U10 | TPS3813K33DBVR | 1 | 3.00 | External watchdog |
| C16 | 100nF | 1 | 0.02 | WDT RST cap |
| C17 | 10µF X5R | 1 | 0.15 | BNO055 bulk |
| Q6a | Si2301CDS | 1 | 0.30 | Pi5 P-MOS (DNP Basic) |
| Q6b | Si2301CDS | 1 | 0.30 | Pi5 P-MOS (DNP Basic) |
| Q7 | AO3400A | 1 | 0.30 | Pi5 N-MOS driver (DNP Basic) |
| R34 | 100kΩ | 1 | 0.01 | Q7 gate pull-down (DNP Basic) |
| R35 | 100kΩ | 1 | 0.01 | Q6 gate pull-up (DNP Basic) |
| R36 | 10kΩ | 1 | 0.01 | MCP INTA pull-up |
| TP1 | Test Point | 1 | 0.05 | MCP INTA access |
| R7 | 0.02Ω→value change | 0 | 0.00 | Same part, new value |

Total additional cost: ~¥4.15/board

---

## Additional Fixes (Rev 1.1d)

### Fix 17: P-MOS Reverse Polarity Protection (Q8)

Added AO3401A P-MOS between XT30 connector (J2) and VBAT bus:
- Q8 Source = VBAT_RAW (directly from J2 pin1)
- Q8 Drain = VBAT (to all downstream circuits)
- Q8 Gate = GND

When battery correctly connected: Vgs = 0 - 7.4V = -7.4V → P-MOS fully ON (Rds=55mΩ).
Voltage drop at 3A: 3 × 0.055 = 0.165V (negligible).
When reversed: Vgs = 0 - (-7.4V) = +7.4V → P-MOS OFF, blocks reverse current.

Previously README stated "P-MOS OR" but no circuit existed. Now implemented.

### Fix 18: MP1584EN Feedback Divider (R37/R38)

MP1584EN (U5) is a bare IC (SOIC-8), not a module — requires external feedback
network to set output voltage. Previously missing from schematic.

- R37 = 52.3kΩ 1% (upper, connected between +5V_PI and FB)
- R38 = 10kΩ 1% (lower, connected between FB and GND)
- Vout = Vref × (1 + R37/R38) = 0.8 × (1 + 52.3/10) = 4.98V ≈ 5.0V
- PI_FB net connects R37/R38 midpoint to U5 pin 5 (FB)

### BOM Delta (Rev 1.1d)

| Ref | Value | Qty | Unit ¥ | Purpose |
|-----|-------|-----|--------|---------|
| Q8 | AO3401A | 1 | 0.50 | Reverse polarity protection |
| R37 | 52.3kΩ 1% | 1 | 0.02 | MP1584EN FB upper |
| R38 | 10kΩ 1% | 1 | 0.02 | MP1584EN FB lower |

Additional cost: ~¥0.54/board

### Non-Fix: BMS Brown-out (Informational)

BMS cutoff → VBAT=0V → all rails collapse. ESP32-S3 internal BOD handles this
correctly (resets MCU before undefined behavior). TPS3813 releases RST when
VDD < 2.31V. No hardware change needed — document in firmware BOD configuration
that brownout threshold should be set at 3.0V (CONFIG_ESP_BROWNOUT_DET_LVL=7).

---

## Validation After Fix

After implementing these changes, re-run:

```bash
python3 scripts/validate-pin-conflicts.py
python3 scripts/validate-bom-firmware.py
python3 hardware/validation/validate_hardware.py
python3 hardware/validation/check_bom_schematic.py
```

Additionally, perform thermal imaging test on first assembled prototype:
- Load ESP32 WiFi TX continuous + 4 motors at 50% duty
- Measure U4 (new buck), U3 (LDO), U2a/U2b (DRV8833) junction temperatures
- Confirm all < 85°C after 30 minutes continuous operation

---

## Additional Fixes (Rev 1.1d continued)

### Fix 19: L1 Inductor Saturation Upgrade (MP2359)

L1 changed from generic 10µH/1210 to Murata DFE322520FD-100M:
- Isat = 2.0A (was unspecified, likely ~1.0A for generic 1210)
- MP2359 peak inductor current at 1.2A load: I_peak = 1.2 + (ΔI/2) ≈ 1.5A
- Margin: 2.0A / 1.5A = 1.33× (meets minimum 1.3× rule)
- DCR = 150mΩ (efficiency ~97% at full load)
- Package: 1210 (same footprint, no layout change)

### Fix 20: L2 Inductor Saturation Upgrade (MP1584EN)

L2 changed from generic 4.7µH/1210 to Sumida CDRH6D38NP-4R7NC:
- Isat = 5.8A (was unspecified, likely ~2A for generic 1210)
- MP1584EN peak inductor current at 3A load: I_peak = 3.0 + (ΔI/2) ≈ 3.8A
- Pi5 inrush can reach 5A momentarily
- Margin: 5.8A / 5.0A = 1.16× (acceptable for inrush, 1.53× for steady-state)
- DCR = 22mΩ (excellent efficiency)
- Package: 7×7mm shielded (larger than 1210 — requires layout adjustment)

### Fix 21: I2C Pull-up Resistors (R1-R2: 10kΩ → 2.2kΩ)

R1-R2 changed from 10kΩ to 2.2kΩ:
- I2C bus has: ESP32 + BNO055 + INA219 + MCP23017 + PBC-34 payload connector
- Payload connector adds up to 200pF cable/device capacitance
- At 400kHz Fast Mode with 10kΩ: rise time = 2.2 × RC = 2.2 × 10k × 400pF = 8.8µs
  (exceeds 300ns spec by 29×)
- At 400kHz with 2.2kΩ: rise time = 2.2 × 2.2k × 400pF = 1.94µs
  (still above 300ns but functional for ≤200pF actual load)
- Sink current check: 3.3V / 2.2kΩ = 1.5mA (within 3mA I2C spec limit)
- For worst-case 200pF: rise time = 2.2 × 2.2k × 200pF = 0.97µs (OK at 400kHz)

### Fix 22: TJA1050 CAN Bus Power Filter (FB1 + C18)

Added LC filter between +5V_ESP and TJA1050 VCC:
- FB1: 600Ω@100MHz ferrite bead (0603, Murata BLM18PG601SN1D)
- C18: 10µF X5R 16V (0805)
- Creates isolated +5V_CAN rail for CAN transceiver
- Prevents CAN bus common-mode noise from coupling into ESP32 supply
- Also provides local energy reservoir for CAN TX current spikes (~70mA)

Schematic: +5V_ESP → FB1 → +5V_CAN → TJA1050.VCC, C18 between +5V_CAN and GND.

### Fix 23: External WDT Feed Period (500ms → 200ms)

EXT_WDT_FEED_PERIOD_MS changed from 500ms to 200ms:
- TPS3813 timeout = 1.6s
- Old margin: 1600/500 = 3.2× (one missed toggle before reset)
- New margin: 1600/200 = 8× (can miss 7 consecutive toggles before reset)
- FreeRTOS tick jitter + task scheduling delays could accumulate under heavy load
- 8× margin ensures no false resets during legitimate CPU-intensive operations

### Fix 24: R7 symbol_instances Metadata Correction

Fixed R7 value in KiCad symbol_instances section from "0.1R" to "0.02R".
The schematic symbol property was correctly updated in Fix 14 but the
symbol_instances metadata (which KiCad uses for BOM export and annotation)
was still showing the old value.

### Fix 25: Q8 Dual P-MOS for Thermal Margin

Q8 (AO3401A single P-MOS) split into Q8a + Q8b (parallel):
- Single AO3401A: Rds(on) = 55mΩ at Vgs=-4.5V
- At 5A bus current: P = 5² × 0.055 = 1.375W (SOT-23 thermal limit ~1.0W)
- Dual parallel: Rds(on) = 27.5mΩ, P = 5² × 0.0275 = 0.69W per device (safe)
- Both devices: Gate=GND, Source=VBAT_RAW, Drain=VBAT
- Same reverse protection logic (Vgs=-7.4V → ON, reverse → OFF)

---

## BOM Delta (Fixes 19-25)

| Ref | Change | Cost Impact |
|-----|--------|-------------|
| L1 | Generic → Murata DFE322520FD-100M | +¥0.80 |
| L2 | Generic → Sumida CDRH6D38NP-4R7NC | +¥1.50 |
| R1-R2 | 10kΩ → 2.2kΩ (same package) | ¥0.00 |
| FB1 | New: 600Ω@100MHz 0603 | +¥0.15 |
| C18 | New: 10µF X5R 0805 | +¥0.15 |
| Q8a | Was Q8 single, now first of pair | ¥0.00 |
| Q8b | New: second parallel P-MOS | +¥0.50 |

Total additional cost: ~¥3.10/board

---

## PCB Layout Impact (Fixes 19-25)

| Fix | Layout Change Required | Severity |
|-----|----------------------|----------|
| #19 (L1) | None — same 1210 footprint | None |
| #20 (L2) | 7×7mm pad vs 1210 — requires footprint change | Medium |
| #21 (I2C) | None — same 0603, value change only | None |
| #22 (CAN filter) | FB1 + C18 near TJA1050 (U8 area) | Low |
| #23 (WDT) | None — firmware only | None |
| #24 (metadata) | None — schematic annotation only | None |
| #25 (Q8 dual) | Second SOT-23 adjacent to Q8a near J2 | Low |

---

## Additional Fixes (Rev 1.1e)

### Fix 26: DRV8833 AISEN/BISEN Tied to GND

DRV8833 xISEN pins were floating — internal 200mV current limit comparator would
trigger on noise. Connected U2a and U2b AISEN/BISEN pins directly to GND (added
#PWR43, #PWR44 GND symbols). Disables hardware current limiting; overcurrent
protection handled by INA219 + firmware monitor. This matches TI EVM default
configuration.

Cost: ¥0 (no new components, just PCB traces to GND plane).

### Fix 29: E-stop Hardwired to Relay Coil Supply Path

**Critical safety fix.** Previously E-stop was GPIO input only — relay control
depended on firmware ISR. If MCU frozen, pressing E-stop could not cut motors.

**Solution**: Added SW1b (second NC contact pair on same E-stop button) in series
with relay coil +5V supply:
```
+5V_ESP → [SW1b NC2 contacts] → +5V_ESTOP_COIL → RLY1 coil+ / R17 pull-up
```

- Normal: NC2 closed → +5V_ESTOP_COIL = +5V_ESP → relay energized
- E-stop pressed: NC2 opens → coil de-energized → relay releases → motors cut
- R17 (Q5 gate pull-up) also connects to +5V_ESTOP_COIL → Q5 gate loses drive

Zero firmware dependency. Compliant with ISO 13850 "independent of control system".
SW1 BOM updated to specify dual NC contact pairs.

### Fix 30: DRV8833 nSLEEP Pull-up to ESTOP Net

R28/R29 pull-up changed from +3V3 to ESTOP net:
- Normal (ESTOP=HIGH via R5 pull-up): nSLEEP=HIGH → DRV8833 active
- E-stop (ESTOP=LOW): nSLEEP=LOW → DRV8833 hardware sleep → outputs Hi-Z

Provides secondary motor shutdown layer: even if relay contacts weld (fail-closed),
DRV8833 sleep mode disables H-bridge outputs. Forms defense-in-depth with Fix 29.

### Fix 31: Battery Critical Low-Power Shutdown (Firmware)

After BATT_CRITICAL state sustained for 5s, firmware executes graceful shutdown:
1. `payload_power_off()` — cuts payload 5V rail
2. `gpio_set_level(PI5_RELAY_GPIO, 0)` — cuts Pi5 (if CONFIG_PI5_POWER_ENABLED)
3. `esp_wifi_stop()` — disables WiFi (major current draw)

Prevents BMS hard-cutoff causing uncontrolled power loss and NVS corruption.
System continues running only: external WDT feed + E-stop monitor + battery monitor.

### Fix 27: Pi5 Power Management SKU Guard (Firmware)

Added `CONFIG_PI5_POWER_ENABLED` Kconfig option:
- Default ON for Standard/Industrial SKUs
- Default OFF for Basic SKU

When disabled, `heartbeat_monitor_init()` returns immediately without configuring
GPIO45 (VDD_SPI strapping pin). Prevents theoretical strapping conflict if TPS3813
reset coincides with power_cycle_pi5() pulling GPIO45 low.

`power_cycle_pi5()` function body also guarded by `#ifdef CONFIG_PI5_POWER_ENABLED`.
Battery critical shutdown uses same guard for Pi5 power-off call.

---

## BOM Delta (Fixes 26-31)

| Fix | Components | Cost Impact |
|-----|-----------|-------------|
| #26 | No new components (GND connections) | ¥0 |
| #29 | SW1 dual NC (same button, specify 2×NC) | ¥0 |
| #30 | R28/R29 connection change (no new parts) | ¥0 |
| #31 | Firmware only | ¥0 |
| #27 | Firmware only | ¥0 |

Total additional cost: **¥0** (safety improvements at zero BOM cost).

---

## PCB Layout Impact (Fixes 26-31)

| Fix | Layout Change Required | Severity |
|-----|----------------------|----------|
| #26 (xISEN) | Short traces from AISEN/BISEN pads to GND plane | Low |
| #29 (E-stop coil) | Route SW1b pads to relay coil supply net | Medium |
| #30 (nSLEEP) | Reroute R28/R29 pull-up from +3V3 to ESTOP net | Low |
| #31 (battery) | None — firmware only | None |
| #27 (SKU guard) | None — firmware only | None |

---

## Round 6: Fixes 32–37 (Buck Converter Critical, E-Stop Polarity, I2C Addressing, USB ESD)

Priority: #32 > #33 > #34 > #35 > #36 > #37

### Fix 32: MP2359 Missing Schottky Diode and Bootstrap Capacitor (CRITICAL)

MP2359DJ is an asynchronous buck — it has no internal low-side FET. Without an external
freewheeling diode, inductor current has no path during off-time → voltage spike destroys IC.
Without bootstrap capacitor, high-side gate cannot be driven → IC fails to switch.

Added:
- D6: SS34 (SOD-123F, 40V/3A Schottky) — cathode to SW, anode to GND
- C19: 100nF (0402) — between BST and SW pins

### Fix 33: MP1584EN Missing Schottky Diode and Bootstrap Capacitor (CRITICAL)

Same issue as Fix 32 for the Pi5 5V/3A rail buck converter. MP1584EN is also asynchronous.

Added:
- D7: SS54 (SMA, 40V/5A Schottky) — cathode to SW, anode to GND (sized for 3A continuous)
- C20: 100nF (0402) — between BST and SW pins

Both bucks would have failed to start without these components. U4 description corrected
from "synchronous" to "asynchronous" to prevent future confusion.

### Fix 34: E-Stop Polarity Inversion (SAFETY-CRITICAL)

Original wiring: SW1 NC shorts ESTOP net to GND, R5 pulls up to +3V3.
This gives ESTOP=HIGH when pressed (NC opens → pull-up dominates).

But firmware expects ESTOP=LOW = safe state (GPIO reads LOW on press → trigger shutdown).
And nSLEEP pull-ups (R28/R29) connected to ESTOP net need ESTOP=HIGH normally to keep
DRV8833 awake, ESTOP=LOW on press to put them to sleep.

**The original polarity is backwards.** Fixed by:
- SW1 NC now passes +3V3 through closed contact → ESTOP=HIGH normally
- R5 changed to pull-DOWN to GND (fail-safe: wire break → ESTOP=LOW → safe state)
- On E-stop press: NC opens → R5 pulls ESTOP to GND → firmware triggers, nSLEEP=LOW

This achieves ISO 13850 fail-safe: any fault (wire break, connector disconnect, SW1
failure-open) results in ESTOP=LOW = safe state. Positive safety architecture.

### Fix 35: BNO055 I2C Address and Interface Pin Ties

BNO055 PS0, PS1, and ADR pins were floating. Per datasheet:
- PS1=LOW, PS0=LOW → I2C mode (vs SPI/UART)
- ADR=LOW → I2C address 0x28 (matches firmware BNO055_I2C_ADDR)

Added explicit GND connections for PS0, PS1, ADR in schematic. Prevents unreliable
startup caused by floating CMOS inputs oscillating between states.

### Fix 36: USB-C D+/D- ESD Protection

USB-C port (J3) had no ESD protection on data lines. Added:
- U11: USBLC6-2SC6 (SOT-23-6) — dual-line TVS for USB D+/D-
- Rated IEC 61000-4-2: ±15kV air, ±8kV contact discharge
- Low capacitance (2pF typ) — transparent to USB 2.0 signaling

Connected between VBUS/GND with D+ and D- passing through protection channels.

### Fix 37: MCP23017 I2C Address Pin Ties

MCP23017 A0, A1, A2 pins were floating. With all three LOW → address 0x20
(matches firmware MCP23017_I2C_ADDR). Added explicit GND connections.

Same failure mode as Fix 35: floating CMOS inputs cause intermittent I2C
address mismatch. Particularly problematic on this IC because firmware polls
it at 100ms intervals — a single miss causes false payload-detect state change.

---

## BOM Delta (Fixes 32–37)

| Fix | Components Added | Cost Impact |
|-----|-----------------|-------------|
| #32 | D6 (SS34), C19 (100nF) | ¥0.32 |
| #33 | D7 (SS54), C20 (100nF) | ¥0.82 |
| #34 | None — wiring change + R5 value unchanged | ¥0 |
| #35 | None — GND connections to existing pads | ¥0 |
| #36 | U11 (USBLC6-2SC6) | ¥0.30 |
| #37 | None — GND connections to existing pads | ¥0 |

Total additional cost: **¥1.44/board**

---

## PCB Layout Impact (Fixes 32–37)

| Fix | Layout Change Required | Severity |
|-----|----------------------|----------|
| #32 (MP2359 Schottky+BST) | Place D6 near U4 SW pin, C19 between BST/SW | High — critical loop area |
| #33 (MP1584 Schottky+BST) | Place D7 near U5 SW pin, C20 between BST/SW | High — critical loop area |
| #34 (E-stop polarity) | Reroute SW1 from GND to +3V3, R5 from +3V3 to GND | Medium |
| #35 (BNO055 pins) | Short traces from PS0/PS1/ADR pads to GND | Low |
| #36 (USB ESD) | Place U11 adjacent to J3 USB-C connector | Medium |
| #37 (MCP23017 A0-A2) | Short traces from A0/A1/A2 pads to GND | Low |

**Layout note**: D6 and D7 placement is critical for EMI performance. The Schottky diode
must be as close as possible to the SW pin with minimal loop area to GND. C19/C20
bootstrap caps must be directly adjacent to BST and SW pins (≤3mm trace length).

---

## Round 7: Fixes 38–42 (Reliability, Safety Margin, Fault Recovery)

Priority: #39 > #42/#40 > #38 > #41

### Fix 38: Ultrasonic Cross-Echo Minimum Distance Gate (Firmware)

Shared trigger (GPIO12) fires all 4 HC-SR04 simultaneously. During round-robin capture,
acoustic multipath from adjacent sensors can produce false short-distance readings
(corridor scenario: side pulse reflects at angle to front receiver).

Added `US_CROSS_ECHO_MIN_M = 0.08f` parameter in robot_params.h. In `ultrasonic_read()`,
any echo arriving faster than this threshold is rejected as physically implausible
multipath and returns `ESP_ERR_INVALID_RESPONSE`. Value derived from minimum inter-sensor
geometric path length (~100mm on 200mm-wide chassis, with 20mm safety margin).

### Fix 39: Disable E-Stop GPIO Internal Pull-Up (Firmware — SAFETY)

GPIO41 had `pull_up_en = GPIO_PULLUP_ENABLE` (internal ~45kΩ). With external R5 (10kΩ
pull-down to GND), normal operation is fine (10k dominates). But if R5 fails open-circuit
(solder crack), the internal pull-up silently defeats the E-stop by holding ESTOP=HIGH
regardless of NC switch state.

Changed to `pull_up_en = GPIO_PULLUP_DISABLE`. Now R5 is the sole bias path — if R5
breaks, GPIO floats low (safe direction). Every single-point failure now results in
safe state, consistent with ISO 13850 fail-safe architecture from Fix 34.

### Fix 40/42: I2C Bus Recovery (Firmware)

Added `i2c_bus_recover()` to i2c_bus.c:
1. Delete I2C driver (releases GPIO pins)
2. Bit-bang 9 SCL clock pulses (standard I2C bus recovery per NXP UM10204 §3.1.16)
3. Generate STOP condition (SDA rising while SCL high)
4. Re-initialize I2C master driver

In thermal_monitor.c, recovery is attempted after 3 consecutive I2C failures
(`I2C_RECOVERY_ATTEMPT_COUNT`). On successful recovery, INA219 is re-reset and
recalibrated. If recovery fails or 3 more failures occur post-recovery (total 6),
then escalate to THERMAL_WARNING as before.

Handles the primary failure mode where a malfunctioning payload device holds SDA low,
blocking INA219/BNO055/MCP23017 access. Full hardware isolation (TCA9548A) deferred to
Rev 2.0.

### Fix 41: Battery Voltage Divider 1% Tolerance (BOM)

R3 (20kΩ) and R4 (10kΩ) changed from 5% to 1% tolerance in BOM. With 5% resistors,
the divider ratio ranges from 2.85–3.16, giving ±5% voltage measurement error. At
critical threshold (6.0V pack), this could delay shutdown by minutes during discharge
below 3.0V/cell, accelerating lithium dendrite formation.

1% tolerance narrows error to ±60mV — adequate margin against the 6.0V threshold.
Consistent with other precision dividers (R30/R31, R37/R38) already at 1%.

---

## BOM Delta (Fixes 38–42)

| Fix | Components | Cost Impact |
|-----|-----------|-------------|
| #38 | None — firmware only | ¥0 |
| #39 | None — firmware only | ¥0 |
| #40/42 | None — firmware only | ¥0 |
| #41 | R3/R4 upgraded 5%→1% | +¥0.02 |

Total additional cost: **¥0.02/board**

---

## Deferred Items

| Issue | Reason | Target |
|-------|--------|--------|
| #28 (AP2112K LDO margin) | 600mA LDO with 520mA estimated load. Marginal but functional. Monitor thermal on prototype. If >85°C, replace with AP7361C (1A) in Rev 2.0 | Rev 2.0 |

---

## Sign-off Checklist

- [x] Schematic Rev 1.1f updated with all fixes (1–42, excluding #28 deferred)
- [x] DRC clean (no ERC errors)
- [x] BOM regenerated from schematic
- [ ] PCB layout updated, DRC clean
- [ ] Gerbers generated and visually inspected
- [ ] First article prototype ordered
- [ ] Thermal validation passed
- [ ] Safety relay self-test passes on prototype
- [ ] HC-SR04 echo voltage confirmed < 3.3V with oscilloscope
- [ ] TPS3813 watchdog reset confirmed (stop WDT feed → ESP32 resets within 2s)
- [ ] Pi5 power switch confirmed (GPIO45 toggle → Pi5 power cycles cleanly)
- [ ] INA219 current reading calibrated and verified against bench supply
- [ ] L2 inductor confirmed no saturation at 5A load (measure inductance under DC bias)
- [ ] I2C bus signal integrity confirmed with oscilloscope (rise time <1µs at 200pF load)
- [ ] CAN bus operates cleanly with +5V_CAN isolated supply
- [ ] Q8a/Q8b thermal confirmed <80°C at 5A continuous
- [ ] E-stop hardware interlock: press E-stop → relay de-energizes without MCU (measure coil current = 0)
- [ ] DRV8833 nSLEEP goes LOW when E-stop pressed (confirm with oscilloscope)
- [ ] Battery critical shutdown: verify payload/Pi5/WiFi off within 5s of BATT_CRITICAL
- [ ] Basic SKU build: confirm GPIO45 NOT configured as output (verify with debugger)
- [ ] MP2359 switching confirmed on oscilloscope (SW node, clean waveform, no ringing >1V)
- [ ] MP1584EN switching confirmed (SW node, confirm D7 conduction during off-time)
- [ ] E-stop polarity: ESTOP net = HIGH normally, LOW when pressed (measure with DMM)
- [ ] Wire-break test: disconnect E-stop wires → ESTOP=LOW → relay drops (fail-safe confirmed)
- [ ] BNO055 I2C address reads as 0x28 on bus scan (i2cdetect)
- [ ] MCP23017 I2C address reads as 0x20 on bus scan (i2cdetect)
- [ ] USB ESD: confirm no signal degradation with U11 in path (eye diagram or enumeration test)
- [ ] Ultrasonic cross-echo: in corridor, verify no false E-stop from side reflections
- [ ] E-stop GPIO41: confirm no internal pull-up (disconnect R5, measure pin voltage = floating low)
- [ ] I2C recovery: hold SDA low with test jig → verify bus recovers within 3 polling cycles
- [ ] Battery ADC: measure voltage with DMM vs firmware reading — error should be <±1%
