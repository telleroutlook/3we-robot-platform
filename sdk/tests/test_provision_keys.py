# SPDX-License-Identifier: Apache-2.0
"""Tests for provision_keys tool."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.provision_keys import (
    NVS_KEY_DTLS_PSK,
    NVS_KEY_OTA_PUBKEY,
    NVS_NAMESPACE_SECURITY,
    PSK_DEFAULT_LENGTH,
    PSK_MIN_LENGTH,
    cmd_batch,
    cmd_flash,
    cmd_generate,
    create_nvs_csv,
    generate_ota_keypair,
    generate_psk,
    main,
)


class TestGeneratePsk:
    def test_default_length(self) -> None:
        psk = generate_psk()
        assert len(psk) == PSK_DEFAULT_LENGTH

    def test_custom_length(self) -> None:
        psk = generate_psk(64)
        assert len(psk) == 64

    def test_returns_bytes(self) -> None:
        psk = generate_psk()
        assert isinstance(psk, bytes)

    def test_randomness(self) -> None:
        psk1 = generate_psk()
        psk2 = generate_psk()
        assert psk1 != psk2


class TestGenerateOtaKeypair:
    def test_returns_tuple(self) -> None:
        private_pem, public_der = generate_ota_keypair()
        assert isinstance(private_pem, bytes)
        assert isinstance(public_der, bytes)

    def test_private_key_is_pem(self) -> None:
        private_pem, _ = generate_ota_keypair()
        assert b"-----BEGIN PRIVATE KEY-----" in private_pem

    def test_public_key_is_der(self) -> None:
        _, public_der = generate_ota_keypair()
        assert len(public_der) > 0
        assert b"-----BEGIN" not in public_der


class TestCreateNvsCsv:
    def test_csv_format(self) -> None:
        psk = b"\x01\x02\x03\x04"
        pubkey = b"\xaa\xbb\xcc"
        result = create_nvs_csv(psk, pubkey)

        lines = result.strip().split("\n")
        assert lines[0] == "key,type,encoding,value"
        assert lines[1] == f"{NVS_NAMESPACE_SECURITY},namespace,,"
        assert lines[2] == f"{NVS_KEY_DTLS_PSK},data,hex2bin,01020304"
        assert lines[3] == f"{NVS_KEY_OTA_PUBKEY},data,hex2bin,aabbcc"

    def test_ends_with_newline(self) -> None:
        result = create_nvs_csv(b"\x00", b"\xff")
        assert result.endswith("\n")


class TestCmdGenerate:
    def test_generates_manifest_and_key(self, tmp_path: Path) -> None:
        output = tmp_path / "device.json"
        args = MagicMock()
        args.output = str(output)

        cmd_generate(args)

        assert output.exists()
        manifest = json.loads(output.read_text())
        assert "psk_hex" in manifest
        assert "ota_public_key_der_hex" in manifest
        assert manifest["psk_length"] == PSK_DEFAULT_LENGTH
        assert manifest["provisioned"] is False

        key_file = output.with_suffix(".key.pem")
        assert key_file.exists()
        key_content = key_file.read_bytes()
        assert b"-----BEGIN PRIVATE KEY-----" in key_content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "dir" / "device.json"
        args = MagicMock()
        args.output = str(output)

        cmd_generate(args)

        assert output.exists()

    def test_key_file_permissions(self, tmp_path: Path) -> None:
        output = tmp_path / "device.json"
        args = MagicMock()
        args.output = str(output)

        cmd_generate(args)

        key_file = output.with_suffix(".key.pem")
        mode = oct(os.stat(key_file).st_mode & 0o777)
        assert mode == "0o600"


class TestCmdFlash:
    def test_missing_manifest_exits(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.keys = str(tmp_path / "nonexistent.json")

        with pytest.raises(SystemExit) as exc_info:
            cmd_flash(args)
        assert exc_info.value.code == 1

    def test_psk_too_short_exits(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "short_psk.json"
        manifest = {
            "psk_hex": "0102",
            "ota_public_key_der_hex": "aabb",
        }
        manifest_path.write_text(json.dumps(manifest))

        args = MagicMock()
        args.keys = str(manifest_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_flash(args)
        assert exc_info.value.code == 1

    def test_all_zero_psk_exits(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "zero_psk.json"
        manifest = {
            "psk_hex": "00" * PSK_MIN_LENGTH,
            "ota_public_key_der_hex": "aabb",
        }
        manifest_path.write_text(json.dumps(manifest))

        args = MagicMock()
        args.keys = str(manifest_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_flash(args)
        assert exc_info.value.code == 1

    def test_dry_run_does_not_flash(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "device.json"
        psk = generate_psk()
        _, pubkey = generate_ota_keypair()
        manifest = {
            "psk_hex": psk.hex(),
            "ota_public_key_der_hex": pubkey.hex(),
            "provisioned": False,
        }
        manifest_path.write_text(json.dumps(manifest))

        args = MagicMock()
        args.keys = str(manifest_path)
        args.port = "/dev/ttyUSB0"
        args.baud = 460800
        args.nvs_offset = "0x9000"
        args.nvs_size = "0x6000"
        args.dry_run = True

        with patch("tools.provision_keys.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            cmd_flash(args)

        reloaded = json.loads(manifest_path.read_text())
        assert reloaded["provisioned"] is False

    def test_successful_flash(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "device.json"
        psk = generate_psk()
        _, pubkey = generate_ota_keypair()
        manifest = {
            "psk_hex": psk.hex(),
            "ota_public_key_der_hex": pubkey.hex(),
        }
        manifest_path.write_text(json.dumps(manifest))

        args = MagicMock()
        args.keys = str(manifest_path)
        args.port = "/dev/ttyUSB0"
        args.baud = 460800
        args.nvs_offset = "0x9000"
        args.nvs_size = "0x6000"
        args.dry_run = False

        with patch("tools.provision_keys.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            cmd_flash(args)

        reloaded = json.loads(manifest_path.read_text())
        assert reloaded["provisioned"] is True
        assert "provisioned_at" in reloaded
        assert reloaded["provisioned_port"] == "/dev/ttyUSB0"

    def test_nvs_gen_failure_exits(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "device.json"
        psk = generate_psk()
        _, pubkey = generate_ota_keypair()
        manifest = {
            "psk_hex": psk.hex(),
            "ota_public_key_der_hex": pubkey.hex(),
        }
        manifest_path.write_text(json.dumps(manifest))

        args = MagicMock()
        args.keys = str(manifest_path)
        args.port = "/dev/ttyUSB0"
        args.baud = 460800
        args.nvs_offset = "0x9000"
        args.nvs_size = "0x6000"
        args.dry_run = False

        with patch("tools.provision_keys.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="gen failed")
            with pytest.raises(SystemExit) as exc_info:
                cmd_flash(args)
            assert exc_info.value.code == 1


class TestCmdBatch:
    def test_batch_generate(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "devices.csv"
        output_dir = tmp_path / "keys"

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["device_id", "mac"])
            writer.writerow(["robot-001", "AA:BB:CC:DD:EE:01"])
            writer.writerow(["robot-002", "AA:BB:CC:DD:EE:02"])

        args = MagicMock()
        args.csv = str(csv_path)
        args.output_dir = str(output_dir)
        args.force = False

        cmd_batch(args)

        assert (output_dir / "robot-001.json").exists()
        assert (output_dir / "robot-002.json").exists()
        assert (output_dir / "robot-001.key.pem").exists()
        assert (output_dir / "robot-002.key.pem").exists()

        m1 = json.loads((output_dir / "robot-001.json").read_text())
        assert m1["device_id"] == "robot-001"
        assert m1["psk_identity"] == "robot-robot-001"
        assert m1["device_mac"] == "AA:BB:CC:DD:EE:01"

    def test_batch_skips_existing(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "devices.csv"
        output_dir = tmp_path / "keys"
        output_dir.mkdir()

        existing = output_dir / "robot-001.json"
        existing.write_text('{"existing": true}')

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["device_id"])
            writer.writerow(["robot-001"])

        args = MagicMock()
        args.csv = str(csv_path)
        args.output_dir = str(output_dir)
        args.force = False

        cmd_batch(args)

        content = json.loads(existing.read_text())
        assert content == {"existing": True}

    def test_batch_force_overwrites(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "devices.csv"
        output_dir = tmp_path / "keys"
        output_dir.mkdir()

        existing = output_dir / "robot-001.json"
        existing.write_text('{"existing": true}')

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["device_id"])
            writer.writerow(["robot-001"])

        args = MagicMock()
        args.csv = str(csv_path)
        args.output_dir = str(output_dir)
        args.force = True

        cmd_batch(args)

        content = json.loads(existing.read_text())
        assert "psk_hex" in content

    def test_batch_missing_csv_exits(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.csv = str(tmp_path / "nope.csv")
        args.output_dir = str(tmp_path / "keys")
        args.force = False

        with pytest.raises(SystemExit) as exc_info:
            cmd_batch(args)
        assert exc_info.value.code == 1

    def test_batch_skips_rows_without_id(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "devices.csv"
        output_dir = tmp_path / "keys"

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "location"])
            writer.writerow(["robot-a", "building-1"])

        args = MagicMock()
        args.csv = str(csv_path)
        args.output_dir = str(output_dir)
        args.force = False

        cmd_batch(args)

        assert not (output_dir / "robot-a.json").exists()


class TestMain:
    def test_generate_subcommand(self, tmp_path: Path) -> None:
        output = tmp_path / "test.json"
        with patch("sys.argv", ["provision-keys", "generate", "--output", str(output)]):
            main()
        assert output.exists()

    def test_no_subcommand_exits(self) -> None:
        with patch("sys.argv", ["provision-keys"]):
            with pytest.raises(SystemExit):
                main()
