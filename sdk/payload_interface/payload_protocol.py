# SPDX-License-Identifier: Apache-2.0
"""PBC-34 Payload Interface - Python reference implementation."""

import struct
import time
from dataclasses import dataclass
from typing import Optional

from .capability_flags import CAP_CAN, CAP_GPIO, CAP_I2C, CAP_SPI, CAP_UART

try:
    import smbus2
except ImportError:
    smbus2 = None


EEPROM_ADDR = 0x50
PAYLOAD_DEFAULT_ADDR = 0x10
FRAME_START = 0xAA
DESCRIPTOR_MAGIC = b"PBC4"


@dataclass(frozen=True)
class PayloadDescriptor:
    """Parsed EEPROM payload descriptor."""

    payload_id: str
    name: str
    power_5v_ma: int
    power_12v_ma: int
    capabilities: int
    gpio_mask: int
    i2c_addr_count: int

    @property
    def uses_i2c(self) -> bool:
        return bool(self.capabilities & CAP_I2C)

    @property
    def uses_spi(self) -> bool:
        return bool(self.capabilities & CAP_SPI)

    @property
    def uses_uart(self) -> bool:
        return bool(self.capabilities & CAP_UART)

    @property
    def uses_gpio(self) -> bool:
        return bool(self.capabilities & CAP_GPIO)

    @property
    def uses_can(self) -> bool:
        return bool(self.capabilities & CAP_CAN)

    @classmethod
    def from_eeprom(cls, data: bytes) -> Optional["PayloadDescriptor"]:
        """Parse raw EEPROM data into a descriptor."""
        if len(data) < 64:
            return None
        if data[0:4] != DESCRIPTOR_MAGIC:
            return None

        version = data[4]
        if version != 0x01:
            return None

        payload_id = data[5:21].rstrip(b"\x00").decode("ascii", errors="replace")
        name = data[0x15:0x35].rstrip(b"\x00").decode("ascii", errors="replace")
        power_5v = struct.unpack(">H", data[0x35:0x37])[0]
        power_12v = struct.unpack(">H", data[0x37:0x39])[0]
        capabilities = data[0x39]
        gpio_mask = data[0x3A]
        i2c_count = data[0x3B]

        return cls(
            payload_id=payload_id,
            name=name,
            power_5v_ma=power_5v,
            power_12v_ma=power_12v,
            capabilities=capabilities,
            gpio_mask=gpio_mask,
            i2c_addr_count=i2c_count,
        )


def crc16_modbus(data: bytes) -> int:
    """Compute CRC-16/MODBUS checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class PayloadInterface:
    """Interface to communicate with a PBC-34 payload device."""

    def __init__(
        self,
        i2c_bus: int = 1,
        eeprom_addr: int = EEPROM_ADDR,
        payload_addr: int = PAYLOAD_DEFAULT_ADDR,
    ):
        if smbus2 is None:
            raise ImportError("smbus2 is required: pip install smbus2")
        self.bus = smbus2.SMBus(i2c_bus)
        self.eeprom_addr = eeprom_addr
        self.payload_addr = payload_addr
        self.descriptor: Optional[PayloadDescriptor] = None

    def discover(self) -> Optional[PayloadDescriptor]:
        """Read EEPROM and parse payload descriptor."""
        try:
            data = bytes(self.bus.read_i2c_block_data(self.eeprom_addr, 0x00, 64))
            self.descriptor = PayloadDescriptor.from_eeprom(data)
            return self.descriptor
        except OSError:
            return None

    def send_command(
        self, cmd_id: int, data: bytes = b"", timeout_ms: int = 100
    ) -> Optional[bytes]:
        """Send a command frame and wait for response.

        Returns the response payload bytes, or None if the command failed
        (I2C error, malformed response, CRC mismatch, or oversized payload).
        Callers must check for None before using the result.
        """
        payload = bytes([cmd_id]) + data
        length = len(payload)
        if length > 29:
            return None
        crc = crc16_modbus(bytes([length]) + payload)
        frame = bytes([FRAME_START, length]) + payload + struct.pack(">H", crc)

        try:
            self.bus.write_i2c_block_data(self.payload_addr, frame[0], list(frame[1:]))
        except OSError:
            return None

        # Wait and read response
        time.sleep(timeout_ms / 1000.0)

        try:
            resp = bytes(self.bus.read_i2c_block_data(self.payload_addr, 0x00, 32))
            if len(resp) < 5 or resp[0] != FRAME_START:
                return None

            resp_len = resp[1]
            if len(resp) < 2 + resp_len + 2:
                return None

            resp_payload = resp[2 : 2 + resp_len]
            resp_crc = struct.unpack(">H", resp[2 + resp_len : 4 + resp_len])[0]

            expected_crc = crc16_modbus(bytes([resp_len]) + resp_payload)
            if resp_crc != expected_crc:
                return None

            return resp_payload
        except OSError:
            return None

    def ping(self) -> bool:
        """Send PING command, check for ACK."""
        resp = self.send_command(0x01)
        return resp is not None and len(resp) > 0 and resp[0] == 0x81

    def get_status(self) -> Optional[bytes]:
        """Request payload status."""
        return self.send_command(0x02)

    def reset(self) -> bool:
        """Send soft reset command."""
        resp = self.send_command(0x05)
        return resp is not None and len(resp) > 0 and resp[0] == 0x81

    def close(self):
        """Close I2C bus."""
        self.bus.close()

    def __enter__(self) -> "PayloadInterface":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
