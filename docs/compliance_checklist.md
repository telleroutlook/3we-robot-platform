# Regulatory Compliance Checklist

> **Status**: In progress (v0.1.0) — checked items are implemented in hardware/firmware design.  
> Unchecked items require third-party lab testing before certification filing.  
> See GitHub Issues labeled `compliance` for tracking.

## EU Radio Equipment Directive (RED) 2014/53/EU

### Article 3.1(a) — Safety (EN 62368-1)
- [x] LVD protection on all power rails (fuses, TVS diodes)
- [x] Emergency stop compliant with ISO 13850 (NC circuit, dual-channel relay)
- [x] Thermal runaway protection (INA219 monitoring, automatic shutdown at 85°C)
- [x] Over-current protection on motor outputs (DRV8833 internal + external)
- [x] ESD protection on all external connectors (TVS arrays on PBC-34)

### Article 3.1(b) — EMC (EN 301 489-1 / EN 301 489-17)
- [ ] Conducted emissions testing (EN 55032 Class B)
- [ ] Radiated emissions testing (EN 55032 Class B)
- [ ] Immunity to ESD (EN 61000-4-2, ±4kV contact, ±8kV air)
- [ ] Immunity to radiated RF (EN 61000-4-3, 3V/m)
- [ ] Immunity to EFT/burst (EN 61000-4-4)
- [ ] PCB 4-layer stack-up with continuous ground plane
- [ ] Ferrite beads on motor power lines
- [ ] 100nF decoupling on all IC VCC pins

### Article 3.2 — Radio (EN 300 328 v2.2.2 for 2.4GHz)
- [x] Wi-Fi module uses certified ESP32-S3 module (FCC/CE/IC pre-certified)
- [ ] Antenna gain documented (PCB trace antenna, <2dBi)
- [ ] Maximum EIRP within 20dBm limit (100mW)
- [ ] Frequency band: 2.400-2.4835 GHz
- [ ] Adaptive Frequency Hopping (AFH) if BLE used

### Article 3.3(d) — Cybersecurity (EN 303 645 / ETSI TS 103 701)
- [x] DTLS 1.2 encryption for wireless control (PSK + AES-128-GCM)
- [x] OTA firmware signing (Ed25519 over SHA-256)
- [x] No default/universal passwords (PSK configured per device)
- [x] Secure boot capability (ESP32 eFuse-based)
- [ ] Vulnerability disclosure policy published
- [ ] Unique per-device identity
- [ ] Software update mechanism documented for end-users
- [ ] No unnecessary network services exposed

## FCC Part 15 (USA)

- [x] ESP32-S3 module FCC ID: verified via module certification
- [ ] FCC label requirements met (15.19)
- [ ] User manual contains FCC statements (15.21, 15.105)
- [ ] Intentional radiator testing (15.247)

## Machinery Directive 2006/42/EC (if robot >10kg or autonomous)

- [x] Risk assessment performed
- [x] Emergency stop function (Category 0)
- [x] Safety relay with self-test diagnostic
- [x] Speed limiting (configurable, 1.2 m/s hard cap)
- [ ] CE marking and Declaration of Conformity
- [ ] Technical construction file

## RoHS (2011/65/EU) / WEEE

- [ ] All components RoHS compliant (verify BOM)
- [ ] Lead-free solder process
- [ ] WEEE symbol on product label
- [ ] Recycling information in user manual

## ISO 13482:2014 — Robots for Personal Care

Applicable if robot operates in close proximity to humans:
- [x] Protective stop function (E-stop + watchdog)
- [x] Speed and force limiting
- [ ] Risk assessment per ISO 12100
- [ ] Protective device testing per ISO 13849-1

## Battery Safety (IEC 62133-2 for Li-ion)

- [ ] Battery protection circuit (over-charge, over-discharge, short circuit)
- [ ] UN38.3 transport testing
- [ ] Battery marking and safety information
- [ ] Charge temperature monitoring

---

## Test Lab Requirements

| Test Category | Standard | Estimated Cost | Lab |
|--------------|----------|---------------|-----|
| EMC Pre-scan | EN 55032 | $500-1000 | Local anechoic chamber |
| EMC Full | EN 55032 + EN 61000-4-x | $3000-5000 | Accredited lab |
| Radio | EN 300 328 | $2000-3000 | Notified Body |
| Safety | EN 62368-1 | $3000-5000 | Accredited lab |
| Cyber | EN 303 645 | $5000-8000 | Specialized lab |

## Timeline for Certification

1. **Week 1-2**: Internal pre-compliance testing (EMC pre-scan, functional safety)
2. **Week 3-4**: Fix issues found in pre-compliance
3. **Week 5-8**: Formal testing at accredited lab
4. **Week 9-10**: Address any test failures
5. **Week 11-12**: Receive test reports, prepare Declaration of Conformity
6. **Week 13**: Apply CE/FCC marks, release to market
