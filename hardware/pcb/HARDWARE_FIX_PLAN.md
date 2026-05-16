# SPDX-License-Identifier: CERN-OHL-P-2.0
# Hardware Fix Plan — Pre-Production Corrections

Status: DRAFT — requires review before PCB re-spin
Date: 2026-05-16
Affects: robot-platform.kicad_sch Rev 1.1, bom_basic.csv, bom_industrial.csv

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

**Recommendation**: All fixes incorporated into Rev 1.1. No deferred items.

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

## Sign-off Checklist

- [ ] Schematic Rev 1.1 updated with all fixes
- [ ] DRC clean (no ERC errors)
- [ ] BOM regenerated from schematic
- [ ] PCB layout updated, DRC clean
- [ ] Gerbers generated and visually inspected
- [ ] First article prototype ordered
- [ ] Thermal validation passed
- [ ] Safety relay self-test passes on prototype
- [ ] HC-SR04 echo voltage confirmed < 3.3V with oscilloscope
