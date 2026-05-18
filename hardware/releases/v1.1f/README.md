# Hardware Release v1.1f — Validation PCB

**Release Date**: 2026-05-18
**Source Commit**: `0471296` (`docs: add repository responsibility split to CLAUDE.md`)
**Status**: Mechanical validation board (no SMT, footprint verification only)

## Purpose

This release locks the exact Gerber files and BOM that were sent to JLCPCB and LCSC on 2026-05-18 for first-pass mechanical verification. The board has no power, no MCU firmware, no active circuits — only mounting holes and footprints for the four key connectors/modules.

## Manufacturing Order

| Item | Vendor | Order # | Amount |
|------|--------|---------|--------|
| 4-layer PCB ×5 | JLCPCB (嘉立创) | Y1 | ¥190.10 |
| Verification components | LCSC (立创商城) | SO26051810421 | ¥34.93 |

## Files in this directory

- `robot-platform-gerber.zip` — exact zip uploaded to JLCPCB
- `positions.csv` — pick-and-place positions (unused for this order, kept for reference)
- `bom-validation.xlsx` — exact BOM uploaded to LCSC

## Validation targets

| Ref | Component | Footprint | Goal |
|-----|-----------|-----------|------|
| J1 | PBC-34 Payload Bus | 2.54mm 1×40 header | Pin alignment |
| J2 | XT30 Battery | 2-pin thru-hole, 5mm pitch, 2mm dia | Hole size + spacing |
| J3 | USB-C | HRO TYPE-C-31-M-12 | SMD pad alignment |
| U1 | ESP32-S3-WROOM-1 | Module footprint | Pad alignment |
| MH1-4 | Mounting holes | M2.5, 2.7mm dia | Screw pass-through |

## Source files

KiCad source at this snapshot:
- `hardware/pcb/robot-platform.kicad_sch`
- `hardware/pcb/robot-platform.kicad_pcb`

To reproduce these gerbers: `bash hardware/manufacturing/generate_gerbers.sh`
(NOT guaranteed to byte-match if KiCad version differs — the locked zip in this directory is authoritative.)
