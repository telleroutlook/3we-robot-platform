#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PBC-34 EEPROM Validator Tool

Validates and programs EEPROM descriptors for PBC-34 payload modules.
Can be used standalone or as part of production test tooling.

Usage:
    python eeprom_validator.py validate <binary_file>
    python eeprom_validator.py generate --id "PAYLOAD_001" --name "Lidar Module" \
        --power-5v 800 --power-12v 0 --caps 0x03 --gpio 0x0F -o payload.bin
    python eeprom_validator.py program --bus 1 --address 0x50 <binary_file>
"""

import argparse
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payload_interface.capability_flags import (
    CAP_GPIO,
    CAP_RESERVED,
    CAPABILITY_NAMES,
)


DESCRIPTOR_MAGIC = b"PBC4"
DESCRIPTOR_SIZE = 64
MAX_PAYLOAD_ID_LEN = 16
MAX_NAME_LEN = 32

# Power limits per rail
MAX_5V_MA = 5000
MAX_12V_MA = 3000


class EepromDescriptor:
    """PBC-34 EEPROM descriptor (64 bytes)."""

    def __init__(self):
        self.magic: bytes = DESCRIPTOR_MAGIC
        self.version: int = 1
        self.payload_id: str = ""
        self.name: str = ""
        self.power_5v_ma: int = 0
        self.power_12v_ma: int = 0
        self.capabilities: int = 0
        self.gpio_mask: int = 0
        self.i2c_addr_count: int = 0

    def to_bytes(self) -> bytes:
        """Serialize descriptor to 64-byte binary."""
        buf = bytearray(DESCRIPTOR_SIZE)

        # Offset 0x00: Magic (4 bytes)
        buf[0:4] = self.magic

        # Offset 0x04: Version (1 byte)
        buf[4] = self.version

        # Offset 0x05: Payload ID (16 bytes, null-padded)
        pid = self.payload_id.encode("ascii", errors="replace")[:MAX_PAYLOAD_ID_LEN]
        buf[5 : 5 + len(pid)] = pid

        # Offset 0x15: Name (32 bytes, null-padded)
        name = self.name.encode("ascii", errors="replace")[:MAX_NAME_LEN]
        buf[0x15 : 0x15 + len(name)] = name

        # Offset 0x35: Power 5V (2 bytes, big-endian)
        struct.pack_into(">H", buf, 0x35, self.power_5v_ma)

        # Offset 0x37: Power 12V (2 bytes, big-endian)
        struct.pack_into(">H", buf, 0x37, self.power_12v_ma)

        # Offset 0x39: Capabilities (1 byte)
        buf[0x39] = self.capabilities

        # Offset 0x3A: GPIO mask (1 byte)
        buf[0x3A] = self.gpio_mask

        # Offset 0x3B: I2C address count (1 byte)
        buf[0x3B] = self.i2c_addr_count

        # Offset 0x3C-0x3F: Reserved (4 bytes)
        return bytes(buf)

    @classmethod
    def from_bytes(cls, data: bytes) -> "EepromDescriptor":
        """Deserialize descriptor from binary data."""
        if len(data) < DESCRIPTOR_SIZE:
            raise ValueError(f"Data too short: {len(data)} < {DESCRIPTOR_SIZE}")

        desc = cls()
        desc.magic = data[0:4]
        desc.version = data[4]
        desc.payload_id = data[5:21].rstrip(b"\x00").decode("ascii", errors="replace")
        desc.name = data[0x15:0x35].rstrip(b"\x00").decode("ascii", errors="replace")
        desc.power_5v_ma = struct.unpack_from(">H", data, 0x35)[0]
        desc.power_12v_ma = struct.unpack_from(">H", data, 0x37)[0]
        desc.capabilities = data[0x39]
        desc.gpio_mask = data[0x3A]
        desc.i2c_addr_count = data[0x3B]
        return desc


class ValidationResult:
    """Result of EEPROM validation."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def print_report(self):
        if self.passed:
            print("VALIDATION PASSED")
        else:
            print("VALIDATION FAILED")

        if self.errors:
            print(f"\n  Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"    [ERROR] {e}")

        if self.warnings:
            print(f"\n  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    [WARN]  {w}")


def validate_descriptor(desc: EepromDescriptor) -> ValidationResult:
    """Validate an EEPROM descriptor against PBC-34 specification."""
    result = ValidationResult()

    # Magic check
    if desc.magic != DESCRIPTOR_MAGIC:
        result.add_error(
            f"Invalid magic: {desc.magic!r} (expected {DESCRIPTOR_MAGIC!r})"
        )

    # Version check
    if desc.version != 1:
        result.add_error(
            f"Unsupported version: {desc.version} (only version 1 is supported)"
        )

    # Payload ID validation
    if not desc.payload_id:
        result.add_error("Payload ID is empty")
    elif len(desc.payload_id) > MAX_PAYLOAD_ID_LEN:
        result.add_error(
            f"Payload ID too long: {len(desc.payload_id)} > {MAX_PAYLOAD_ID_LEN}"
        )
    elif not desc.payload_id.isascii():
        result.add_error("Payload ID contains non-ASCII characters")

    # Name validation
    if not desc.name:
        result.add_warning("Payload name is empty")
    elif len(desc.name) > MAX_NAME_LEN:
        result.add_error(f"Payload name too long: {len(desc.name)} > {MAX_NAME_LEN}")
    elif not desc.name.isascii():
        result.add_error("Payload name contains non-ASCII characters")

    # Power budget validation
    if desc.power_5v_ma > MAX_5V_MA:
        result.add_error(
            f"5V power exceeds limit: {desc.power_5v_ma}mA > {MAX_5V_MA}mA"
        )
    elif desc.power_5v_ma > 3000:
        result.add_warning(
            f"5V power is high: {desc.power_5v_ma}mA (>60% of {MAX_5V_MA}mA budget)"
        )

    if desc.power_12v_ma > MAX_12V_MA:
        result.add_error(
            f"12V power exceeds limit: {desc.power_12v_ma}mA > {MAX_12V_MA}mA"
        )
    elif desc.power_12v_ma > 2000:
        result.add_warning(
            f"12V power is high: {desc.power_12v_ma}mA (>66% of {MAX_12V_MA}mA budget)"
        )

    # Total power budget
    total_power_w = (desc.power_5v_ma * 5.0 + desc.power_12v_ma * 12.0) / 1000.0
    if total_power_w > 50.0:
        result.add_error(f"Total power exceeds 50W: {total_power_w:.1f}W")
    elif total_power_w > 35.0:
        result.add_warning(f"Total power is high: {total_power_w:.1f}W (>70% budget)")

    # Capabilities validation
    if desc.capabilities & CAP_RESERVED:
        result.add_warning("Reserved capability bit is set")

    # GPIO mask validation
    if desc.gpio_mask != 0 and not (desc.capabilities & CAP_GPIO):
        result.add_warning("GPIO mask is non-zero but GPIO capability not declared")

    return result


def print_descriptor(desc: EepromDescriptor):
    """Print human-readable descriptor information."""
    print(f"  Magic:        {desc.magic.decode('ascii', errors='replace')}")
    print(f"  Version:      {desc.version}")
    print(f"  Payload ID:   {desc.payload_id}")
    print(f"  Name:         {desc.name}")
    print(f"  5V Power:     {desc.power_5v_ma} mA")
    print(f"  12V Power:    {desc.power_12v_ma} mA")
    total_w = (desc.power_5v_ma * 5.0 + desc.power_12v_ma * 12.0) / 1000.0
    print(f"  Total Power:  {total_w:.1f} W")
    caps = []
    for bit, name in CAPABILITY_NAMES.items():
        if desc.capabilities & bit:
            caps.append(name)
    print(
        f"  Capabilities: {', '.join(caps) if caps else 'None'} (0x{desc.capabilities:02X})"
    )
    print(f"  GPIO Mask:    0x{desc.gpio_mask:02X} ({bin(desc.gpio_mask)})")


def cmd_validate(args):
    """Validate an EEPROM binary file."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    data = path.read_bytes()
    if len(data) < DESCRIPTOR_SIZE:
        print(f"Error: File too small ({len(data)} bytes, need {DESCRIPTOR_SIZE})")
        return 1

    print(f"Validating: {path}")
    print(f"File size:  {len(data)} bytes\n")

    desc = EepromDescriptor.from_bytes(data)
    print("Descriptor contents:")
    print_descriptor(desc)
    print()

    result = validate_descriptor(desc)
    result.print_report()
    return 0 if result.passed else 1


def cmd_generate(args):
    """Generate an EEPROM binary file."""
    desc = EepromDescriptor()
    desc.payload_id = args.id
    desc.name = args.name
    desc.power_5v_ma = args.power_5v
    desc.power_12v_ma = args.power_12v
    desc.capabilities = args.caps
    desc.gpio_mask = args.gpio

    # Validate before writing
    result = validate_descriptor(desc)
    if not result.passed:
        print("Generated descriptor fails validation:")
        result.print_report()
        return 1

    data = desc.to_bytes()
    output = Path(args.output)
    output.write_bytes(data)

    print(f"Generated EEPROM descriptor: {output}")
    print(f"Size: {len(data)} bytes\n")
    print("Descriptor contents:")
    print_descriptor(desc)

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  [WARN] {w}")

    return 0


def cmd_program(args):
    """Program EEPROM via I2C (requires smbus2)."""
    try:
        import smbus2
    except ImportError:
        print("Error: smbus2 not installed. Run: pip install smbus2")
        return 1

    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    data = path.read_bytes()
    desc = EepromDescriptor.from_bytes(data)
    result = validate_descriptor(desc)
    if not result.passed:
        print("EEPROM data fails validation - aborting programming")
        result.print_report()
        return 1

    try:
        bus_num = int(args.bus)
        eeprom_addr = int(args.address, 0)
    except ValueError as exc:
        print(f"Error: Invalid bus or address: {exc}")
        return 1

    print(f"Programming EEPROM at I2C bus {bus_num}, address 0x{eeprom_addr:02X}")
    print_descriptor(desc)
    print()

    confirm = input("Proceed? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted.")
        return 0

    bus = smbus2.SMBus(bus_num)
    try:
        # Write in 16-byte pages (AT24C02 page size)
        page_size = 16
        for offset in range(0, len(data), page_size):
            chunk = data[offset : offset + page_size]
            msg = smbus2.i2c_msg.write(eeprom_addr, [offset] + list(chunk))
            bus.i2c_rdwr(msg)
            time.sleep(0.005)  # 5ms write cycle time

        # Verify
        read_msg = smbus2.i2c_msg.write(eeprom_addr, [0])
        read_data = smbus2.i2c_msg.read(eeprom_addr, DESCRIPTOR_SIZE)
        bus.i2c_rdwr(read_msg, read_data)
        readback = bytes(read_data)

        if readback == data[:DESCRIPTOR_SIZE]:
            print("Programming complete - verification PASSED")
            return 0
        else:
            print("Programming FAILED - readback mismatch")
            return 1
    finally:
        bus.close()


def main():
    parser = argparse.ArgumentParser(
        description="PBC-34 EEPROM Validator and Programmer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate command
    p_validate = subparsers.add_parser("validate", help="Validate EEPROM binary")
    p_validate.add_argument("file", help="Path to EEPROM binary file")

    # generate command
    p_generate = subparsers.add_parser("generate", help="Generate EEPROM binary")
    p_generate.add_argument("--id", required=True, help="Payload ID (max 16 chars)")
    p_generate.add_argument("--name", required=True, help="Payload name (max 32 chars)")
    p_generate.add_argument(
        "--power-5v", type=int, default=0, help="5V current draw (mA)"
    )
    p_generate.add_argument(
        "--power-12v", type=int, default=0, help="12V current draw (mA)"
    )
    p_generate.add_argument(
        "--caps",
        type=lambda x: int(x, 0),
        default=0,
        help="Capabilities bitmask (hex, e.g., 0x0F)",
    )
    p_generate.add_argument(
        "--gpio", type=lambda x: int(x, 0), default=0, help="GPIO mask (hex)"
    )
    p_generate.add_argument(
        "-o", "--output", default="payload_eeprom.bin", help="Output file path"
    )

    # program command
    p_program = subparsers.add_parser("program", help="Program EEPROM via I2C")
    p_program.add_argument("file", help="Path to EEPROM binary file")
    p_program.add_argument("--bus", default="1", help="I2C bus number (default: 1)")
    p_program.add_argument("--address", default="0x50", help="EEPROM I2C address")

    args = parser.parse_args()

    if args.command == "validate":
        sys.exit(cmd_validate(args))
    elif args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "program":
        sys.exit(cmd_program(args))


if __name__ == "__main__":
    main()
