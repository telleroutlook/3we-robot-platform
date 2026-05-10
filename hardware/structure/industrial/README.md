# Industrial SKU Chassis — Mechanical Drawings

Placeholder directory for the 500×400×100mm Industrial chassis CAD exports.

## Target Specifications

| Parameter | Value |
|-----------|-------|
| Chassis dimensions | 500 × 400 × 100 mm |
| Material | 6061-T6 aluminum, 3mm sheet |
| Finish | Black anodized |
| Wheel diameter | 97mm Mecanum |
| Track width | 320 mm |
| Wheelbase | 300 mm |
| Mounting grid | M4 threaded inserts, 25mm pitch |
| Payload pattern | 120×120mm, 4× M4 |
| IP rating | IP54 (gaskets on all panel joints) |

## Expected DXF Files (to be generated from 3D model)

- `chassis_industrial_bottom.dxf` — Bottom plate (500×400mm, 3mm 6061-T6)
- `chassis_industrial_top.dxf` — Top plate with payload mount holes
- `chassis_industrial_front.dxf` — Front panel with cable gland cutouts
- `chassis_industrial_rear.dxf` — Rear panel with USB-C and power cutouts
- `chassis_industrial_side.dxf` — Side panels (×2)
- `motor_bracket_550.dxf` — 37mm mount bracket for 550 gear motors
- `payload_plate_industrial.dxf` — 120×120mm payload mounting plate

## Notes

- PCB is identical across all SKUs (same 120×90mm mainboard)
- Cable gland positions: 6× PG9, 3 per side
- Battery bay sized for 4S 5000mAh LiPo (dual bay option)
- Motor axle height matches 97mm wheel center (48.5mm from base)
