# SPDX-License-Identifier: Apache-2.0
"""Tests for payload_interface.payload_protocol module."""

from unittest.mock import patch

import pytest

from payload_interface.capability_flags import (
    CAP_CAN,
    CAP_GPIO,
    CAP_I2C,
    CAP_SPI,
    CAP_UART,
)
from payload_interface.payload_protocol import (
    FRAME_START,
    PayloadDescriptor,
    PayloadInterface,
    crc16_modbus,
)


class TestCrc16Modbus:
    def test_empty_bytes(self):
        assert crc16_modbus(b"") == 0xFFFF

    def test_known_vector_123456789(self):
        # Standard MODBUS test vector
        assert crc16_modbus(b"123456789") == 0x4B37

    def test_single_byte(self):
        result = crc16_modbus(b"\x01")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_long_payload(self):
        data = bytes(range(256))
        result = crc16_modbus(data)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_deterministic(self):
        data = b"hello world"
        assert crc16_modbus(data) == crc16_modbus(data)


class TestPayloadDescriptorFromEeprom:
    def test_valid_full_parse(self, valid_eeprom_bytes):
        desc = PayloadDescriptor.from_eeprom(valid_eeprom_bytes)
        assert desc is not None
        assert desc.payload_id == "test-payload-01"
        assert desc.name == "Test Sensor Array"
        assert desc.power_5v_ma == 500
        assert desc.power_12v_ma == 0
        assert desc.capabilities == 0x01
        assert desc.gpio_mask == 0x03
        assert desc.i2c_addr_count == 2

    def test_too_short(self):
        assert PayloadDescriptor.from_eeprom(b"\x00" * 63) is None

    def test_bad_magic(self):
        data = bytearray(64)
        data[0:4] = b"XXXX"
        assert PayloadDescriptor.from_eeprom(bytes(data)) is None

    def test_bad_version(self):
        data = bytearray(64)
        data[0:4] = b"PBC4"
        data[4] = 0x02
        assert PayloadDescriptor.from_eeprom(bytes(data)) is None

    def test_version_one_accepted(self, valid_eeprom_bytes):
        desc = PayloadDescriptor.from_eeprom(valid_eeprom_bytes)
        assert desc is not None

    def test_capabilities_i2c(self):
        data = bytearray(64)
        data[0:4] = b"PBC4"
        data[4] = 0x01
        data[0x39] = CAP_I2C | CAP_SPI
        desc = PayloadDescriptor.from_eeprom(bytes(data))
        assert desc is not None
        assert desc.uses_i2c is True
        assert desc.uses_spi is True
        assert desc.uses_uart is False
        assert desc.uses_gpio is False
        assert desc.uses_can is False

    def test_capabilities_all(self):
        data = bytearray(64)
        data[0:4] = b"PBC4"
        data[4] = 0x01
        data[0x39] = CAP_I2C | CAP_SPI | CAP_UART | CAP_GPIO | CAP_CAN
        desc = PayloadDescriptor.from_eeprom(bytes(data))
        assert desc is not None
        assert desc.uses_i2c is True
        assert desc.uses_spi is True
        assert desc.uses_uart is True
        assert desc.uses_gpio is True
        assert desc.uses_can is True


class TestPayloadInterface:
    def test_init_without_smbus_raises(self):
        with patch("payload_interface.payload_protocol.smbus2", None):
            with pytest.raises(ImportError, match="smbus2"):
                PayloadInterface()

    def test_init_success(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        assert iface.bus is mock_smbus
        assert iface.descriptor is None

    def test_discover_valid(self, mock_smbus, valid_eeprom_bytes):
        mock_smbus.read_i2c_block_data.return_value = list(valid_eeprom_bytes)
        iface = PayloadInterface(i2c_bus=1)
        desc = iface.discover()
        assert desc is not None
        assert desc.payload_id == "test-payload-01"
        assert iface.descriptor is desc

    def test_discover_oserror(self, mock_smbus):
        mock_smbus.read_i2c_block_data.side_effect = OSError("I2C error")
        iface = PayloadInterface(i2c_bus=1)
        assert iface.discover() is None

    def test_send_command_too_long(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        result = iface.send_command(0x01, data=b"\x00" * 255)
        assert result is None

    def test_send_command_write_oserror(self, mock_smbus):
        mock_smbus.write_i2c_block_data.side_effect = OSError("Write fail")
        iface = PayloadInterface(i2c_bus=1)
        result = iface.send_command(0x01, data=b"\x00")
        assert result is None

    def test_send_command_valid_response(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        # Build a valid response frame: [0xAA, len, payload..., crc_hi, crc_lo]
        resp_payload = bytes([0x81])
        resp_len = len(resp_payload)
        crc = crc16_modbus(bytes([resp_len]) + resp_payload)
        frame = [FRAME_START, resp_len] + list(resp_payload) + [crc >> 8, crc & 0xFF]
        # Pad to 32 bytes (read length)
        frame.extend([0] * (32 - len(frame)))
        mock_smbus.read_i2c_block_data.return_value = frame
        result = iface.send_command(0x01, timeout_ms=1)
        assert result == b"\x81"

    def test_send_command_bad_start_byte(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        frame = [0x00] + [0] * 31
        mock_smbus.read_i2c_block_data.return_value = frame
        result = iface.send_command(0x01, timeout_ms=1)
        assert result is None

    def test_send_command_bad_crc(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        resp_payload = bytes([0x81])
        resp_len = len(resp_payload)
        frame = [FRAME_START, resp_len] + list(resp_payload) + [0xFF, 0xFF]
        frame.extend([0] * (32 - len(frame)))
        mock_smbus.read_i2c_block_data.return_value = frame
        result = iface.send_command(0x01, timeout_ms=1)
        assert result is None

    def test_send_command_truncated_response(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        frame = [FRAME_START, 30] + [0] * 3  # claims 30 bytes but only 5 total
        mock_smbus.read_i2c_block_data.return_value = frame
        result = iface.send_command(0x01, timeout_ms=1)
        assert result is None

    def test_send_command_read_oserror(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        mock_smbus.write_i2c_block_data.return_value = None
        mock_smbus.read_i2c_block_data.side_effect = OSError("Read fail")
        result = iface.send_command(0x01, timeout_ms=1)
        assert result is None

    def test_ping_success(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        resp_payload = bytes([0x81])
        resp_len = len(resp_payload)
        crc = crc16_modbus(bytes([resp_len]) + resp_payload)
        frame = [FRAME_START, resp_len] + list(resp_payload) + [crc >> 8, crc & 0xFF]
        frame.extend([0] * (32 - len(frame)))
        mock_smbus.read_i2c_block_data.return_value = frame
        assert iface.ping() is True

    def test_ping_failure(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        mock_smbus.read_i2c_block_data.side_effect = OSError("fail")
        # send_command will fail on write first
        mock_smbus.write_i2c_block_data.side_effect = OSError("fail")
        assert iface.ping() is False

    def test_get_status(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        status_data = bytes([0x02, 0x01, 0x00])
        resp_len = len(status_data)
        crc = crc16_modbus(bytes([resp_len]) + status_data)
        frame = [FRAME_START, resp_len] + list(status_data) + [crc >> 8, crc & 0xFF]
        frame.extend([0] * (32 - len(frame)))
        mock_smbus.read_i2c_block_data.return_value = frame
        result = iface.get_status()
        assert result == status_data

    def test_reset_success(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        resp_payload = bytes([0x81])
        resp_len = len(resp_payload)
        crc = crc16_modbus(bytes([resp_len]) + resp_payload)
        frame = [FRAME_START, resp_len] + list(resp_payload) + [crc >> 8, crc & 0xFF]
        frame.extend([0] * (32 - len(frame)))
        mock_smbus.read_i2c_block_data.return_value = frame
        assert iface.reset() is True

    def test_close(self, mock_smbus):
        iface = PayloadInterface(i2c_bus=1)
        iface.close()
        mock_smbus.close.assert_called_once()
