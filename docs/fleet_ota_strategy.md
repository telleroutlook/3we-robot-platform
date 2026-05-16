# Fleet OTA Strategy

> For single-device OTA implementation details (pre-flight checks, signing, validation window), see [firmware_guide.md — OTA Update](firmware_guide.md#ota-update).

This document defines the over-the-air firmware update strategy for production fleet deployments.

## Update Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Build Server │     │ Update Server│     │   Robots     │
│              │     │ (HTTPS CDN)  │     │              │
│ sign + build ├────►│ host binary  ├────►│ verify + OTA │
│              │     │              │     │ A/B partition │
└──────────────┘     └──────────────┘     └──────────────┘
```

## Version Compatibility

| Firmware Version | Protocol Version | Compatible App Versions |
|-----------------|------------------|------------------------|
| 0.1.x | 1 | 0.1.x companion |
| 0.2.x | 1 | 0.1.x, 0.2.x companion |
| 1.0.x | 2 | 1.0.x+ companion |

Rules:
- Minor versions maintain backward compatibility within the same major
- Major version bumps may break protocol (require coordinated companion update)
- Firmware advertises protocol version; companion checks compatibility before triggering OTA

## Staged Rollout Process

### Phase 1: Internal Validation
- Deploy to 1-2 internal test robots
- Run 24-hour stability test
- Verify diagnostics telemetry reports healthy status
- Gate: all test robots report DiagnosticStatus.OK for 24h

### Phase 2: Canary (10%)
- Deploy to 10% of fleet (randomly selected)
- Monitor for 48 hours
- Compare error rates against control group
- Gate: no increase in ERROR/WARN diagnostics vs control

### Phase 3: Wider Rollout (50%)
- Deploy to 50% of fleet
- Monitor for 24 hours
- Gate: no regressions in topic rates, battery life, or safety events

### Phase 4: Full Fleet (100%)
- Deploy to remaining robots
- Monitor for 24 hours post-completion
- Mark release as stable

## Rollback Triggers

Automatically halt rollout and trigger rollback if any of:
- Safety E-stop triggered without operator action (firmware bug)
- Boot loop detected (>3 reboots in 5 minutes)
- DTLS handshake failure rate > 5%
- Battery drain rate > 2x baseline
- Diagnostics topic stops publishing for > 60s

## ESP-IDF A/B Partition Scheme

```
┌─────────────────────────────────────────────────┐
│ Bootloader │ OTA Data │ Factory │ OTA_0 │ OTA_1 │
│            │          │ (app)   │ (app) │ (app) │
└─────────────────────────────────────────────────┘
```

- `Factory`: Initial firmware flashed at manufacturing
- `OTA_0` / `OTA_1`: Alternating partitions for updates
- `OTA Data`: Tracks which partition is active

### Boot Validation Flow

1. New firmware boots from OTA partition
2. 30-second validation window: safety self-test, relay check, sensor initialization
3. If validation passes (safety NORMAL, motors idle, no boot fail escalation): `esp_ota_mark_app_valid_cancel_rollback()`
4. If validation fails or firmware crashes: reboot triggers automatic rollback to previous partition
5. After 3 consecutive boot failures (tracked in NVS): firmware refuses to self-confirm, watchdog resets to previous partition

## OTA Trigger Mechanisms

### 1. Scheduled Check (Recommended)
- Robot checks update server every 6 hours
- URL: `https://updates.robot-platform.org/v1/check?sku={sku}&version={current_version}`
- Response includes download URL and expected SHA-256
- Update only proceeds if battery > 50%

### 2. Push via MQTT
- Fleet management sends MQTT message to `fleet/{robot_id}/commands/ota`
- Payload: `{"url": "...", "sha256": "...", "version": "0.2.1"}`
- Robot validates and initiates download

### 3. Manual via ROS2 Service
- Operator calls: `ros2 service call /ota/trigger robot_interfaces/srv/OtaTrigger "{url: '...'}"``

## Firmware Signing

All OTA images must be signed with ECDSA P-256:

```bash
# Generate signing key (one-time, store securely)
openssl ecparam -name prime256v1 -genkey -noout -out ota_signing_key.pem

# Extract public key (provision to devices)
openssl ec -in ota_signing_key.pem -pubout -outform DER -out ota_pubkey.der

# Sign a firmware binary
python3 scripts/sign_firmware.py \
  --input build/robot-platform.bin \
  --key ota_signing_key.pem \
  --output build/robot-platform-signed.bin \
  --version 0.2.1
```

The signed binary format:
```
[Magic: 0x524F424F] [Version: semver] [Image Size] [SHA-256 Hash] [ECDSA Signature] [Firmware Data]
```

## Update Server Requirements

- HTTPS only (TLS 1.2+)
- CDN-backed for fleet scale
- Version manifest endpoint: returns latest version per SKU
- Binary download with range request support (resume interrupted downloads)
- Rate limiting: max 100 downloads per robot per day

## Monitoring OTA Health

Track in fleet dashboard:
- Update success rate (target: >99%)
- Average download time
- Rollback rate (target: <1%)
- Fleet version distribution (pie chart)
- Time to full fleet deployment

## Emergency Procedures

### Critical Bug in Deployed Firmware

1. **Halt rollout** immediately (remove binary from update server)
2. **Push rollback command** via MQTT to all affected robots
3. If MQTT unreachable: robots auto-rollback after boot failure
4. **Root cause analysis** before re-deploying fix
5. Document incident in `CHANGELOG.md`

### Signing Key Compromise

1. **Revoke** the compromised key from update server
2. **Generate** new signing key pair
3. **OTA push** firmware with new public key embedded (signed with old key — last use)
4. **Verify** all devices now have new public key
5. **Destroy** old private key from all storage locations
