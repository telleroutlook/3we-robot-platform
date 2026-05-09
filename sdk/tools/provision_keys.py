# SPDX-License-Identifier: Apache-2.0
"""
Key provisioning tool for 3WE Robot Platform devices.

Generates and flashes per-device DTLS PSK and OTA public keys to ESP32 NVS.
Outputs a JSON inventory manifest for fleet tracking.

Usage:
    provision-keys generate --output keys/device_001.json
    provision-keys flash --port /dev/ttyUSB0 --keys keys/device_001.json
    provision-keys batch --csv devices.csv --output-dir keys/
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


NVS_NAMESPACE_SECURITY = "security"
NVS_KEY_DTLS_PSK = "dtls_psk"
NVS_KEY_OTA_PUBKEY = "ota_pubkey"
PSK_MIN_LENGTH = 16
PSK_DEFAULT_LENGTH = 32


def generate_psk(length: int = PSK_DEFAULT_LENGTH) -> bytes:
    """Generate a cryptographically random PSK."""
    psk = secrets.token_bytes(length)
    if all(b == 0 for b in psk):
        raise RuntimeError("Generated all-zero PSK (astronomically unlikely, retry)")
    return psk


def generate_ota_keypair() -> tuple[bytes, bytes]:
    """
    Generate an ECDSA P-256 key pair for OTA signing.
    Returns (private_key_pem, public_key_der).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Error: 'cryptography' package required for key generation.")
        print("Install: pip install cryptography")
        sys.exit(1)

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_der


def create_nvs_csv(psk: bytes, ota_pubkey: bytes) -> str:
    """Create NVS partition CSV content for esptool's nvs_partition_gen."""
    lines = [
        "key,type,encoding,value",
        f"{NVS_NAMESPACE_SECURITY},namespace,,",
        f"{NVS_KEY_DTLS_PSK},data,hex2bin,{psk.hex()}",
        f"{NVS_KEY_OTA_PUBKEY},data,hex2bin,{ota_pubkey.hex()}",
    ]
    return "\n".join(lines) + "\n"


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate keys and save to JSON manifest."""
    psk = generate_psk(PSK_DEFAULT_LENGTH)
    ota_private_pem, ota_public_der = generate_ota_keypair()

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "psk_hex": psk.hex(),
        "psk_length": len(psk),
        "ota_public_key_der_hex": ota_public_der.hex(),
        "ota_public_key_length": len(ota_public_der),
        "device_mac": None,
        "psk_identity": None,
        "provisioned": False,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n")

    private_key_path = output_path.with_suffix(".key.pem")
    private_key_path.write_bytes(ota_private_pem)
    os.chmod(private_key_path, 0o600)

    print("Keys generated:")
    print(f"  Manifest: {output_path}")
    print(f"  OTA signing key (KEEP SECRET): {private_key_path}")
    print(f"  PSK length: {len(psk)} bytes")
    print(f"  OTA public key length: {len(ota_public_der)} bytes")


def cmd_flash(args: argparse.Namespace) -> None:
    """Flash keys to device NVS via esptool/nvs_partition_gen."""
    manifest_path = Path(args.keys)
    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())
    psk = bytes.fromhex(manifest["psk_hex"])
    ota_pubkey = bytes.fromhex(manifest["ota_public_key_der_hex"])

    if len(psk) < PSK_MIN_LENGTH:
        print(f"Error: PSK too short ({len(psk)} bytes, minimum {PSK_MIN_LENGTH})")
        sys.exit(1)

    if all(b == 0 for b in psk):
        print("Error: PSK is all zeros (invalid)")
        sys.exit(1)

    nvs_csv = create_nvs_csv(psk, ota_pubkey)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "nvs_keys.csv"
        bin_path = Path(tmpdir) / "nvs_keys.bin"
        csv_path.write_text(nvs_csv)

        nvs_size = args.nvs_size or "0x6000"

        print(f"Generating NVS partition binary ({nvs_size} bytes)...")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "esp_idf_nvs_partition_gen",
                "generate",
                str(csv_path),
                str(bin_path),
                nvs_size,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "nvs_partition_gen",
                    "generate",
                    str(csv_path),
                    str(bin_path),
                    nvs_size,
                ],
                capture_output=True,
                text=True,
            )

        if result.returncode != 0:
            print(f"Error generating NVS binary: {result.stderr}")
            print(
                "Ensure ESP-IDF tools are in PATH or install: pip install esp-idf-nvs-partition-gen"
            )
            sys.exit(1)

        nvs_offset = args.nvs_offset or "0x9000"

        print(f"Flashing NVS to device at offset {nvs_offset}...")
        flash_cmd = [
            "esptool.py",
            "--port",
            args.port,
            "--baud",
            str(args.baud),
            "write_flash",
            nvs_offset,
            str(bin_path),
        ]

        if args.dry_run:
            print(f"  DRY RUN: {' '.join(flash_cmd)}")
        else:
            result = subprocess.run(flash_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error flashing: {result.stderr}")
                sys.exit(1)

            print("NVS keys flashed successfully.")

            manifest["provisioned"] = True
            manifest["provisioned_at"] = datetime.now(timezone.utc).isoformat()
            manifest["provisioned_port"] = args.port
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Manifest updated: {manifest_path}")


def cmd_batch(args: argparse.Namespace) -> None:
    """Batch generate keys for multiple devices from a CSV."""
    import csv

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            device_id = row.get("device_id") or row.get("id") or row.get("mac")
            if not device_id:
                print("Warning: Row missing device_id/id/mac, skipping")
                continue

            safe_name = device_id.replace(":", "-").replace("/", "-")
            output_file = output_dir / f"{safe_name}.json"

            if output_file.exists() and not args.force:
                print(f"  Skip (exists): {output_file}")
                continue

            psk = generate_psk(PSK_DEFAULT_LENGTH)
            ota_private_pem, ota_public_der = generate_ota_keypair()

            manifest = {
                "device_id": device_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "psk_hex": psk.hex(),
                "psk_length": len(psk),
                "psk_identity": f"robot-{device_id}",
                "ota_public_key_der_hex": ota_public_der.hex(),
                "ota_public_key_length": len(ota_public_der),
                "device_mac": row.get("mac"),
                "provisioned": False,
            }

            output_file.write_text(json.dumps(manifest, indent=2) + "\n")

            private_key_path = output_file.with_suffix(".key.pem")
            private_key_path.write_bytes(ota_private_pem)
            os.chmod(private_key_path, 0o600)

            print(f"  Generated: {output_file}")

    print(f"\nBatch complete. Keys in: {output_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="provision-keys",
        description="3WE Robot Platform — Device Key Provisioning Tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate", help="Generate PSK + OTA key pair")
    gen_parser.add_argument(
        "--output", "-o", required=True, help="Output JSON manifest path"
    )

    flash_parser = subparsers.add_parser("flash", help="Flash keys to device NVS")
    flash_parser.add_argument(
        "--keys", "-k", required=True, help="JSON manifest from generate"
    )
    flash_parser.add_argument(
        "--port", "-p", default="/dev/ttyUSB0", help="Serial port"
    )
    flash_parser.add_argument(
        "--baud", "-b", type=int, default=460800, help="Baud rate"
    )
    flash_parser.add_argument(
        "--nvs-offset", help="NVS partition offset (default: 0x9000)"
    )
    flash_parser.add_argument("--nvs-size", help="NVS partition size (default: 0x6000)")
    flash_parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )

    batch_parser = subparsers.add_parser("batch", help="Batch generate keys from CSV")
    batch_parser.add_argument(
        "--csv", required=True, help="CSV with device_id/mac columns"
    )
    batch_parser.add_argument(
        "--output-dir", "-o", required=True, help="Output directory"
    )
    batch_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing keys"
    )

    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "flash": cmd_flash,
        "batch": cmd_batch,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
