# Mechanical Structure Documentation

## Overall Dimensions (Basic/Standard/Pro)

| Parameter | Value |
|-----------|-------|
| Length | 300 mm |
| Width | 250 mm |
| Height (base only) | 80 mm |
| Height (with payload) | 150 mm max |
| Ground clearance | 25 mm |
| Weight (basic, no battery) | 1.2 kg |
| Weight (fully loaded) | 3.5 kg max |

## Industrial SKU Dimensions

| Parameter | Value |
|-----------|-------|
| Length | 500 mm |
| Width | 400 mm |
| Height (base only) | 100 mm |
| Height (with payload) | 200 mm max |
| Ground clearance | 48.5 mm |
| Weight (no battery) | 3.5 kg |
| Weight (fully loaded) | 18.5 kg max |
| Track width | 320 mm |
| Wheelbase | 300 mm |

## Chassis

- Material: 6061 aluminum alloy, 2mm sheet (CNC bent)
- Finish: Black anodized
- Alternative: 3D printed PLA/PETG for prototyping
- Industrial: 3mm sheet for increased rigidity

## Mounting Pattern

### Basic/Standard/Pro

- M3 threaded inserts on 20mm grid
- 4× M3 payload mounting holes (80×80mm pattern, centered)
- 2× M3 battery bracket mounts (each side)
- PCB standoffs: M2.5 × 8mm (4 points)

### Industrial

- M4 threaded inserts on 25mm grid
- 4× M4 payload mounting holes (120×120mm pattern, centered)
- 4× M4 battery bracket mounts (each side, dual-battery support)
- PCB standoffs: M2.5 × 8mm (4 points, same PCB)

## Wheel Configuration

```
        Front
   ╲FL         FR╱
    ┌───────────┐
    │           │
    │  Chassis  │
    │           │
    └───────────┘
   ╱RL         RR╲
        Rear
```

### Basic/Standard/Pro

- Wheel type: 48mm Mecanum (45° roller angle)
- Roller direction: FL/RR = left-handed, FR/RL = right-handed
- Wheel-to-chassis mount: M3 × 12mm axle with D-shaft coupling
- Motor mount: 25mm N20 bracket with M2 screws

### Industrial

- Wheel type: 97mm Mecanum (45° roller angle, aluminum hub + PU rollers)
- Roller direction: FL/RR = left-handed, FR/RL = right-handed
- Wheel-to-chassis mount: M4 × 6mm D-shaft with set screw hub
- Motor mount: 37mm bracket for 550 gear motors, M3 screws

## Load Capacity

| SKU | Max Payload | Recommended Payload |
|-----|-------------|-------------------|
| Basic | 1.0 kg | 0.5 kg |
| Standard | 2.0 kg | 1.5 kg |
| Pro | 3.0 kg | 2.0 kg |
| Industrial | 15.0 kg | 10.0 kg |

## Clearance and Obstacles

- Maximum step height: 5 mm (48mm wheels, Basic/Standard/Pro)
- Maximum step height: 15 mm (97mm wheels, Industrial)
- Maximum slope: 15° (with load centering)
- Maximum slope: 20° (Industrial, with low CG payload)
- Turning radius: 0 mm (omnidirectional, rotates in place)

## IP Rating

| SKU | Rating | Notes |
|-----|--------|-------|
| Basic | IP20 | Indoor use only |
| Standard | IP20 | Indoor use only |
| Pro | IP40 | Dust protected |
| Industrial | IP54 | Splash resistant |

## Assembly Reference Points

- Origin: Center of base_link (geometric center of chassis, ground level)
- X-axis: Forward
- Y-axis: Left
- Z-axis: Up (ROS REP-103 compliant)

## Cable Management

- Internal cable routing channels (10mm wide)
- Strain relief for motor cables (zip tie anchors)
- Battery connector accessible from bottom panel
- USB-C programming port accessible from rear
