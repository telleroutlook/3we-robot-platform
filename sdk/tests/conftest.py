# SPDX-License-Identifier: Apache-2.0
"""Shared test fixtures for PBC-34 SDK tests."""

import struct
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_smbus():
    """Provide a mocked SMBus instance."""
    with patch("payload_interface.payload_protocol.smbus2") as mock_mod:
        mock_bus = MagicMock()
        mock_mod.SMBus.return_value = mock_bus
        yield mock_bus


@pytest.fixture
def valid_eeprom_bytes() -> bytes:
    """Return a valid 64-byte EEPROM descriptor."""
    buf = bytearray(64)
    buf[0:4] = b"PBC4"
    buf[4] = 0x01
    buf[5:20] = b"test-payload-01"
    buf[0x15:0x2C] = b"Test Sensor Array\x00" + b"\x00" * 6
    struct.pack_into(">H", buf, 0x35, 500)
    struct.pack_into(">H", buf, 0x37, 0)
    buf[0x39] = 0x01  # CAP_I2C
    buf[0x3A] = 0x03  # GPIO mask
    buf[0x3B] = 2  # i2c_addr_count
    return bytes(buf)


@pytest.fixture
def tmp_binary_file(tmp_path, valid_eeprom_bytes):
    """Write a valid EEPROM descriptor to a temp file."""
    p = tmp_path / "test_payload.bin"
    p.write_bytes(valid_eeprom_bytes)
    return p
