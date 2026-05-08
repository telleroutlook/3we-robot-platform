# Mechanical Structure Documentation

## Overall Dimensions

| Parameter | Value |
|-----------|-------|
| Length | 300 mm |
| Width | 250 mm |
| Height (base only) | 80 mm |
| Height (with payload) | 150 mm max |
| Ground clearance | 25 mm |
| Weight (basic, no battery) | 1.2 kg |
| Weight (fully loaded) | 3.5 kg max |

## Chassis

- Material: 6061 aluminum alloy, 2mm sheet (CNC bent)
- Finish: Black anodized
- Alternative: 3D printed PLA/PETG for prototyping

## Mounting Pattern

- M3 threaded inserts on 20mm grid
- 4× M3 payload mounting holes (80×80mm pattern, centered)
- 2× M3 battery bracket mounts (each side)
- PCB standoffs: M2.5 × 8mm (4 points)

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

- Wheel type: 48mm Mecanum (45° roller angle)
- Roller direction: FL/RR = left-handed, FR/RL = right-handed
- Wheel-to-chassis mount: M3 × 12mm axle with D-shaft coupling
- Motor mount: 25mm N20 bracket with M2 screws

## Load Capacity

| SKU | Max Payload | Recommended Payload |
|-----|-------------|-------------------|
| Basic | 1.0 kg | 0.5 kg |
| Standard | 2.0 kg | 1.5 kg |
| Pro | 3.0 kg | 2.0 kg |
| Industrial | 5.0 kg | 3.0 kg |

## Clearance and Obstacles

- Maximum step height: 5 mm (48mm wheels)
- Maximum slope: 15° (with load centering)
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
