# SPDX-License-Identifier: Apache-2.0
"""Tests for tools.eeprom_validator module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.eeprom_validator import (
    DESCRIPTOR_SIZE,
    EepromDescriptor,
    validate_descriptor,
)


class TestEepromDescriptorSerialization:
    def test_to_bytes_size_always_64(self):
        desc = EepromDescriptor()
        desc.payload_id = "TEST"
        desc.name = "Test"
        data = desc.to_bytes()
        assert len(data) == DESCRIPTOR_SIZE

    def test_roundtrip(self):
        desc = EepromDescriptor()
        desc.payload_id = "LIDAR_V2"
        desc.name = "Lidar Module"
        desc.power_5v_ma = 800
        desc.power_12v_ma = 200
        desc.capabilities = 0x03
        desc.gpio_mask = 0x0F

        data = desc.to_bytes()
        loaded = EepromDescriptor.from_bytes(data)

        assert loaded.magic == b"PBC4"
        assert loaded.version == 1
        assert loaded.payload_id == "LIDAR_V2"
        assert loaded.name == "Lidar Module"
        assert loaded.power_5v_ma == 800
        assert loaded.power_12v_ma == 200
        assert loaded.capabilities == 0x03
        assert loaded.gpio_mask == 0x0F

    def test_from_bytes_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            EepromDescriptor.from_bytes(b"\x00" * 63)

    def test_payload_id_truncated(self):
        desc = EepromDescriptor()
        desc.payload_id = "A" * 20  # exceeds 16
        data = desc.to_bytes()
        loaded = EepromDescriptor.from_bytes(data)
        assert len(loaded.payload_id) <= 16

    def test_name_truncated(self):
        desc = EepromDescriptor()
        desc.payload_id = "TEST"
        desc.name = "X" * 40  # exceeds 32
        data = desc.to_bytes()
        loaded = EepromDescriptor.from_bytes(data)
        assert len(loaded.name) <= 32


class TestValidateDescriptor:
    def _make_valid(self) -> EepromDescriptor:
        desc = EepromDescriptor()
        desc.payload_id = "SENSOR_01"
        desc.name = "Temperature Sensor"
        desc.power_5v_ma = 100
        desc.power_12v_ma = 0
        desc.capabilities = 0x01
        desc.gpio_mask = 0x00
        return desc

    def test_valid_passes(self):
        desc = self._make_valid()
        result = validate_descriptor(desc)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_bad_magic(self):
        desc = self._make_valid()
        desc.magic = b"XXXX"
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("magic" in e.lower() for e in result.errors)

    def test_bad_version(self):
        desc = self._make_valid()
        desc.version = 99
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("version" in e.lower() for e in result.errors)

    def test_empty_payload_id(self):
        desc = self._make_valid()
        desc.payload_id = ""
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_long_payload_id(self):
        desc = self._make_valid()
        desc.payload_id = "A" * 17
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("too long" in e.lower() for e in result.errors)

    def test_non_ascii_payload_id(self):
        desc = self._make_valid()
        desc.payload_id = "héllo"
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("ascii" in e.lower() for e in result.errors)

    def test_empty_name_warning(self):
        desc = self._make_valid()
        desc.name = ""
        result = validate_descriptor(desc)
        assert result.passed is True
        assert any("empty" in w.lower() for w in result.warnings)

    def test_5v_over_limit(self):
        desc = self._make_valid()
        desc.power_5v_ma = 5001
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("5v" in e.lower() for e in result.errors)

    def test_12v_over_limit(self):
        desc = self._make_valid()
        desc.power_12v_ma = 3001
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("12v" in e.lower() for e in result.errors)

    def test_total_power_over_50w(self):
        desc = self._make_valid()
        desc.power_5v_ma = 5000
        desc.power_12v_ma = 3000
        # 5000*5 + 3000*12 = 25000 + 36000 = 61W
        result = validate_descriptor(desc)
        assert result.passed is False
        assert any("50w" in e.lower() for e in result.errors)

    def test_high_5v_power_warning(self):
        desc = self._make_valid()
        desc.power_5v_ma = 2500  # >60% of 3000mA limit, triggers warning
        result = validate_descriptor(desc)
        assert result.passed is True
        assert any("high" in w.lower() for w in result.warnings)

    def test_reserved_cap_warning(self):
        desc = self._make_valid()
        desc.capabilities = 0x80  # CAP_RESERVED
        result = validate_descriptor(desc)
        assert result.passed is True
        assert any("reserved" in w.lower() for w in result.warnings)

    def test_gpio_mask_without_capability(self):
        desc = self._make_valid()
        desc.capabilities = 0x01  # I2C only, no GPIO
        desc.gpio_mask = 0x0F
        result = validate_descriptor(desc)
        assert result.passed is True
        assert any("gpio" in w.lower() for w in result.warnings)


class TestCmdValidate:
    def test_valid_file(self, tmp_binary_file, capsys):
        from tools.eeprom_validator import cmd_validate

        class Args:
            file = str(tmp_binary_file)

        result = cmd_validate(Args())
        assert result == 0
        captured = capsys.readouterr()
        assert "PASSED" in captured.out

    def test_file_not_found(self, tmp_path, capsys):
        from tools.eeprom_validator import cmd_validate

        class Args:
            file = str(tmp_path / "nonexistent.bin")

        result = cmd_validate(Args())
        assert result == 1

    def test_invalid_file(self, tmp_path, capsys):
        from tools.eeprom_validator import cmd_validate

        bad_file = tmp_path / "bad.bin"
        bad_file.write_bytes(b"XXXX" + b"\x00" * 60)

        class Args:
            file = str(bad_file)

        result = cmd_validate(Args())
        assert result == 1
        captured = capsys.readouterr()
        assert "FAILED" in captured.out


class TestCmdGenerate:
    def test_valid_generation(self, tmp_path):
        from tools.eeprom_validator import cmd_generate

        output_path = tmp_path / "output.bin"
        args = type(
            "Args",
            (),
            {
                "id": "TEST_GEN",
                "name": "Generated",
                "power_5v": 100,
                "power_12v": 0,
                "caps": 0x01,
                "gpio": 0x00,
                "output": str(output_path),
            },
        )()

        result = cmd_generate(args)
        assert result == 0
        assert output_path.exists()
        assert len(output_path.read_bytes()) == DESCRIPTOR_SIZE

    def test_invalid_rejects(self, tmp_path, capsys):
        from tools.eeprom_validator import cmd_generate

        output_path = tmp_path / "output.bin"
        args = type(
            "Args",
            (),
            {
                "id": "",
                "name": "Test",
                "power_5v": 100,
                "power_12v": 0,
                "caps": 0x00,
                "gpio": 0x00,
                "output": str(output_path),
            },
        )()

        result = cmd_generate(args)
        assert result == 1
        assert not output_path.exists()
