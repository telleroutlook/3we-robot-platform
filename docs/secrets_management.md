# Secrets Management

This document describes how cryptographic keys and credentials flow through the 3WE Robot Platform in development and production environments.

## Key Material Overview

| Secret | Storage Location | Purpose | Rotation |
|--------|-----------------|---------|----------|
| DTLS PSK | Device NVS (`security/dtls_psk`) | Encrypts control channel | Re-provision + OTA |
| OTA Public Key | Device NVS (`security/ota_pubkey`) | Verifies firmware updates | Re-provision only |
| OTA Private Key | Secure offline storage | Signs firmware releases | Replace + re-provision fleet |
| Wi-Fi Password | Device NVS (`wifi/password`) | Network access | Captive portal re-provision |
| Secure Boot Key | ESP32 eFuse (one-time write) | Validates bootloader | Cannot rotate (hardware fuse) |

## Development Environment

In development, security features are relaxed for ease of iteration:

1. **Wi-Fi**: Compile-time fallback via `CONFIG_WIFI_SSID` / `CONFIG_WIFI_PASSWORD` in Kconfig
2. **DTLS**: Can boot without PSK (control channel unencrypted, logged as error)
3. **OTA**: Can boot without public key (firmware updates disabled)
4. **NVS**: Unencrypted (readable via `esptool.py read_flash`)
5. **Secure Boot**: Disabled (unsigned firmware accepted)

## Production Environment

Production builds (`CONFIG_PRODUCTION_BUILD=y`) enforce:

1. **Wi-Fi**: NVS-only provisioning (Kconfig fallback disabled at compile time)
2. **DTLS**: Required — device refuses to start control listener without valid PSK
3. **OTA**: Required — unsigned firmware images rejected at bootloader level
4. **NVS**: Encrypted (`CONFIG_NVS_ENCRYPTION=y`) — at-rest protection for all keys
5. **Secure Boot**: Enabled (`CONFIG_SECURE_BOOT_V2_ENABLED=y`) — only signed bootloader/app runs

## Key Provisioning Workflow

### Per-Device Provisioning

Use the `provision-keys` CLI tool (installed with `pip install robot-payload-sdk[provision]`):

```bash
# 1. Generate unique keys for a device
provision-keys generate --output keys/device_001.json

# 2. Flash keys to device NVS via UART
provision-keys flash --keys keys/device_001.json --port /dev/ttyUSB0

# 3. Batch generation for fleet
provision-keys batch --csv devices.csv --output-dir keys/
```

### Generated Files

After `generate`, two files are created:
- `device_001.json` — Manifest with PSK hex, OTA public key hex, provisioning status
- `device_001.key.pem` — OTA signing private key (**KEEP SECRET**, chmod 600)

### Device Inventory

Each manifest JSON contains:
```json
{
  "device_id": "robot-AA:BB:CC:DD:EE:FF",
  "psk_hex": "...",
  "psk_identity": "robot-AA:BB:CC:DD:EE:FF",
  "ota_public_key_der_hex": "...",
  "provisioned": true,
  "provisioned_at": "2025-01-15T10:30:00Z"
}
```

Store manifests in a secure, access-controlled location (not in the git repository).

## NVS Encryption

When `CONFIG_NVS_ENCRYPTION=y` is set:
- ESP-IDF generates an NVS encryption key on first boot (stored in a dedicated flash partition)
- All NVS read/write operations are transparently encrypted
- A flash dump cannot recover key material without the encryption key

**Recovery**: If the NVS encryption key is lost or corrupted, the device must be fully erased and re-provisioned. There is no recovery path.

## Key Rotation

### Rotating DTLS PSK

1. Generate new PSK: `provision-keys generate --output keys/device_001_v2.json`
2. Push new PSK via OTA config update (future feature) or re-flash NVS
3. Update fleet inventory
4. Old PSK immediately invalid after NVS write

### Rotating OTA Signing Key

1. Generate new key pair
2. Build new firmware signed with **both** old and new keys (dual-sign transition period)
3. OTA push firmware that accepts the new public key
4. Push firmware that writes new public key to NVS
5. Subsequent OTA images signed with new key only
6. Revoke old key from signing infrastructure

**Note**: OTA public key rotation requires careful staged rollout. A mis-signed OTA leaves devices unable to update.

## CI/CD Secrets

### GitHub Actions

| Secret | Purpose | Where Used |
|--------|---------|-----------|
| `PYPI_TOKEN` | Publish SDK to PyPI | `release.yml` (or OIDC trusted publisher) |
| `OTA_SIGNING_KEY` | Sign release firmware | `release.yml` firmware-build job |

Configure via: Repository → Settings → Secrets and variables → Actions

### Local Development

Copy `.env.example` to `.env` and fill in local values. The `.env` file is gitignored.

## Security Best Practices

1. **Never commit keys** — `.gitignore` includes `*.pem`, `*.key`, `keys/`
2. **Principle of least privilege** — CI only gets secrets it needs per job
3. **Audit access** — Review who can access signing keys quarterly
4. **Backup signing keys** — Store OTA private keys in at least 2 secure locations
5. **Monitor provisioning** — Track which devices have been provisioned via inventory manifests
6. **Incident response** — If a signing key is compromised, rotate immediately and OTA all devices
