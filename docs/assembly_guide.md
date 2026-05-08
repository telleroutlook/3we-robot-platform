# Assembly Guide

Step-by-step hardware assembly instructions for the robot-platform.

## Tools Required

- Phillips screwdriver (PH1, PH2)
- Hex key set (M2, M2.5, M3)
- Soldering iron (for motor wires)
- Wire strippers
- Multimeter
- 3D printer (for custom brackets, optional)

## Parts Checklist

Before starting, verify you have all components from the appropriate BOM file:
- `hardware/bom/bom_basic.csv` (Basic SKU)
- `hardware/bom/bom_standard.csv` (Standard SKU - includes everything in Basic)
- `hardware/bom/bom_pro.csv` (Pro SKU)
- `hardware/bom/bom_industrial.csv` (Industrial SKU)

---

## Step 1: Chassis Preparation

1. Inspect the aluminum chassis for burrs or bent edges
2. Install M2.5 brass standoffs (×4) for PCB mounting
3. Install M3 threaded inserts (×4) for payload mounting plate
4. Verify all mounting holes align with the 20mm grid pattern

## Step 2: Motor Installation

Motor orientation is critical for correct mecanum movement:

```
        FRONT
   [FL ╲]     [╱ FR]
   ┌──────────────┐
   │              │
   │   CHASSIS    │
   │              │
   └──────────────┘
   [╱ RL]     [RR ╲]
        REAR
```

1. Mount motors in their brackets using M2 screws
2. Secure brackets to chassis corners with M3×8mm bolts
3. Route motor wires through internal cable channels
4. Solder JST-PH connectors to motor leads:
   - **Red** → Motor+ (positive terminal)
   - **Black** → Motor- (negative terminal)
   - **Green** → Encoder A
   - **White** → Encoder B
   - **Red (thin)** → Encoder VCC (3.3V)
   - **Black (thin)** → Encoder GND

## Step 3: Wheel Mounting

**Critical: Mecanum roller direction matters!**

- Front-Left & Rear-Right: Left-handed rollers (╲ pattern when viewed from front)
- Front-Right & Rear-Left: Right-handed rollers (╱ pattern when viewed from front)

1. Press wheel onto motor D-shaft
2. Secure with M3 set screw (use threadlocker)
3. Verify wheel spins freely without wobble
4. Check ground clearance ≥ 25mm

## Step 4: PCB Installation

1. Place mainboard on standoffs
2. Secure with M2.5 nylon screws (to avoid shorts)
3. Connect motor cables to JST headers (match FL/FR/RL/RR labels)
4. Connect encoder cables to their respective headers
5. Verify no cables are pinched or strained

## Step 5: Sensor Installation

### Ultrasonic Sensors (×4)

1. Mount HC-SR04 modules at chassis corners, facing outward
2. Use 3D-printed brackets or hot-glue for secure mounting
3. Connect to mainboard ultrasonic header (4-pin: VCC, Trig, Echo, GND)
4. Ensure sensor faces are perpendicular to ground (±5° tolerance)

### IMU (BNO055)

1. Mount at geometric center of chassis, as flat as possible
2. Secure with M2 screws or double-sided tape (vibration-resistant)
3. Connect I2C cable (4-pin: VCC, GND, SDA, SCL)
4. Note mounting orientation (arrow on PCB = forward/X-axis)

## Step 6: Battery Installation

1. Insert 18650 cells into battery holder (observe polarity!)
2. Verify BMS LED indicates correct voltage
3. Mount battery pack centrally (lowest possible for CG)
4. Secure with velcro strap or 3D-printed retention clip
5. Route XT30 cable to mainboard power input
6. **DO NOT connect yet** — wait until final inspection

## Step 7: Emergency Stop Wiring

This is a safety-critical step. Double-check all connections.

```
E-Stop Button (NC contact)
    Pin 1 ──→ Safety Relay Coil (+)
    Pin 2 ──→ Safety Relay Coil (-)
                    │
Safety Relay NO Contact:
    COM ──→ Battery VBAT (7.4V)
    NO  ──→ DRV8833 Motor Power Input
```

1. Mount E-stop button on chassis top (accessible, labeled)
2. Wire NC contact to safety relay coil terminals
3. Wire relay NO contact in series with motor power line
4. Verify: When button is UP (normal), relay energized, motors powered
5. Verify: When button is DOWN (pressed), relay de-energized, motors cut

## Step 8: PBC-34 Connector

1. Mount the 2×17 header on the top payload plate
2. Wire according to pinout in `hardware/pcb/README.md`
3. Install keying mechanism (plastic tab in position 17)
4. Test continuity on power pins (1-6) before energizing

## Step 9: Final Inspection

Before powering on for the first time:

- [ ] All motor wires connected and secure
- [ ] Battery polarity correct
- [ ] E-stop button wired correctly (NC)
- [ ] No loose wires or exposed conductors
- [ ] No cables interfering with wheel rotation
- [ ] All screws tightened
- [ ] Ultrasonic sensors unobstructed
- [ ] IMU mounted flat and centered

### First Power-On Procedure

1. Press E-stop button DOWN (motors locked out)
2. Connect battery XT30 connector
3. Verify power LED on mainboard illuminates
4. Check ESP32 serial output for boot messages
5. Verify all sensor readings are reasonable
6. Release E-stop button (twist to reset)
7. Test motor movement with low speed commands

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No power LED | Battery disconnected or BMS tripped | Check XT30, verify cell voltage |
| Motors don't spin | E-stop active or relay wiring | Check relay state, verify NC wiring |
| Wrong movement direction | Motor wires swapped | Swap IN1/IN2 wires for affected motor |
| Robot curves when going straight | Wheel type swapped | Verify roller direction (Step 3) |
| Ultrasonic reads max | Wiring reversed or sensor blocked | Check Echo/Trig pins, clear obstacles |
| IMU drift | Bad mounting or calibration | Re-mount flat, run calibration routine |
