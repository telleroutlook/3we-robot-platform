# IP54 Manufacturing Specification

> SPDX-License-Identifier: CERN-OHL-P-2.0

## Scope

This document defines the IP54 environmental protection requirements for the Industrial SKU enclosure. IP54 provides protection against dust ingress (limited) and water splashing from any direction.

## Conformal Coating (PCB)

| Parameter | Specification |
|-----------|--------------|
| Material | Polyurethane (PU) |
| Thickness | 25–75 μm |
| Coverage | All exposed traces and components (excluding connectors, test pads) |
| Vendor process | JLCPCB conformal coating add-on (+¥8/board) |
| Standard | IPC-CC-830C Class 1 |

### Exclusion zones (no coating)

- All through-hole connectors (XT30, GH1.25, JST-XH)
- Programming headers (JTAG, UART)
- Test points marked TP1–TP12
- Thermal pads on BTS7960 / heatsink contact areas
- NTC thermistor sensing surface

## Enclosure Sealing

| Component | Specification |
|-----------|--------------|
| Enclosure material | 6061-T6 aluminum, black anodize |
| Dimensions | 500 × 400 × 100 mm (as per bom_industrial.csv) |
| Seal type | Silicone O-ring, Shore A 50, continuous perimeter |
| Seal groove | 2.5 mm wide × 1.8 mm deep, machined into lower half |
| Fastener sealing | M3 screws with silicone washers |
| Cable entry | IP67 cable glands (PG7 for signal, PG9 for power) |

## Connectors

| Interface | Connector Type | IP Rating |
|-----------|---------------|-----------|
| Motor power | XT60 with silicone boot | IP67 |
| Signal cables | GH1.25 with potted headers | IP54 |
| Antenna (5G) | SMA with O-ring gasket | IP67 |
| Charging | XT30 with dust cap | IP54 (capped) |

## Pressure Equalization

| Parameter | Specification |
|-----------|--------------|
| Vent type | Gore-Tex PTFE membrane (ePTFE) |
| Part number | Gore PolyVent PMF Series or equivalent |
| Location | Bottom panel, away from spray direction |
| Air flow | ≥ 200 mL/min |
| Water entry pressure | > 0.5 bar |

## Forced Ventilation

| Parameter | Specification |
|-----------|--------------|
| Fan | 40 mm × 10 mm, 5V DC, 0.1A |
| Intake | Filtered (IP54 dust mesh, 0.5 mm aperture) |
| Exhaust | PTFE membrane vent (above) |
| Airflow direction | Intake over BTS7960 heatsinks → exhaust |

## Validation

### Standard Tests

| Test | Standard | Criteria |
|------|----------|----------|
| Dust protection | IEC 60529 (IP5X) | No harmful dust deposit after 8h |
| Water splash | IEC 60529 (IPX4) | No water ingress, all directions, 5 min |
| Salt fog | IEC 60068-2-11 | 48h, 5% NaCl, 35°C — no corrosion on connectors |
| Vibration | IEC 60068-2-6 | 10–150 Hz, 1g, 3 axes, 2h per axis |
| Shock | IEC 60068-2-27 | 30g, 11ms half-sine, 3 axes |

### Inspection Checklist

- [ ] Conformal coat coverage verified under UV lamp
- [ ] O-ring seated without gaps or twists
- [ ] Cable glands torqued to spec
- [ ] Vent membrane installed, not punctured
- [ ] Fan intake mesh clean and secured
- [ ] All fastener silicone washers present
