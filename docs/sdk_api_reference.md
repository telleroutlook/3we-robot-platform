# SDK API Reference — PBC-34 Payload Interface

Python reference implementation for communicating with PBC-34 payload devices via I2C.

## Installation

```bash
pip install smbus2
```

The SDK has no other runtime dependencies.

## Module: `payload_interface.payload_protocol`

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `EEPROM_ADDR` | `0x50` | Default I2C address for payload EEPROM |
| `PAYLOAD_DEFAULT_ADDR` | `0x10` | Default I2C address for payload communication |
| `FRAME_START` | `0xAA` | Frame start byte for command protocol |
| `DESCRIPTOR_MAGIC` | `b"PBC4"` | Expected magic bytes in EEPROM descriptor |

### Class: `PayloadDescriptor`

Frozen dataclass representing a parsed EEPROM payload descriptor.

```python
from sdk.payload_interface.payload_protocol import PayloadDescriptor
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `payload_id` | `str` | Unique identifier (max 16 chars, ASCII) |
| `name` | `str` | Human-readable name (max 32 chars, ASCII) |
| `power_5v_ma` | `int` | Maximum 5V rail current draw in milliamps |
| `power_12v_ma` | `int` | Maximum 12V rail current draw in milliamps |
| `capabilities` | `int` | Bitmask of capability flags |
| `gpio_mask` | `int` | Bitmask of used GPIO pins |
| `i2c_addr_count` | `int` | Number of additional I2C addresses used |

#### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `uses_i2c` | `bool` | Payload uses I2C slave interface |
| `uses_spi` | `bool` | Payload uses SPI slave interface |
| `uses_uart` | `bool` | Payload uses UART |
| `uses_gpio` | `bool` | Payload uses GPIO pins |
| `uses_can` | `bool` | Payload uses CAN bus |

#### Class Methods

##### `from_eeprom(data: bytes) -> Optional[PayloadDescriptor]`

Parse raw EEPROM data (minimum 64 bytes) into a descriptor.

Returns `None` if:
- Data is less than 64 bytes
- Magic bytes do not match `b"PBC4"`
- Version byte is not `0x01`

**Example:**

```python
raw = read_eeprom_bytes(addr=0x50, offset=0, length=64)
desc = PayloadDescriptor.from_eeprom(raw)
if desc:
    print(f"Payload: {desc.name} (ID: {desc.payload_id})")
    print(f"Power budget: {desc.power_5v_ma}mA @5V, {desc.power_12v_ma}mA @12V")
```

---

### Class: `PayloadInterface`

I2C communication handler for PBC-34 payload devices.

```python
from sdk.payload_interface.payload_protocol import PayloadInterface
```

#### Constructor

```python
PayloadInterface(
    i2c_bus: int = 1,
    eeprom_addr: int = 0x50,
    payload_addr: int = 0x10,
)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `i2c_bus` | `1` | Linux I2C bus number (`/dev/i2c-N`) |
| `eeprom_addr` | `0x50` | I2C address of the payload EEPROM |
| `payload_addr` | `0x10` | I2C address for command communication |

Raises `ImportError` if `smbus2` is not installed.

#### Methods

##### `discover() -> Optional[PayloadDescriptor]`

Read the EEPROM at `eeprom_addr` and parse the 64-byte descriptor. Stores the result in `self.descriptor`.

Returns `None` on I2C error or invalid descriptor.

##### `send_command(cmd_id: int, data: bytes = b"", timeout_ms: int = 100) -> Optional[bytes]`

Send a framed command and read the response.

**Frame format:**

```
[0xAA] [LENGTH] [CMD_ID] [DATA...] [CRC16_H] [CRC16_L]
```

- `LENGTH`: byte count of `[CMD_ID] + [DATA]`
- CRC: CRC-16/MODBUS computed over `[LENGTH][CMD_ID][DATA]`

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `cmd_id` | Command byte (e.g., `0x01` for PING) |
| `data` | Optional payload bytes |
| `timeout_ms` | Time to wait before reading response |

Returns the response payload bytes (without framing) or `None` on error.

##### `ping() -> bool`

Send PING command (`0x01`). Returns `True` if ACK (`0x81`) received.

##### `get_status() -> Optional[bytes]`

Send STATUS command (`0x02`). Returns raw status bytes or `None`.

##### `reset() -> bool`

Send RESET command (`0x05`). Returns `True` if ACK received.

##### `close() -> None`

Close the I2C bus handle. Always call when done (or use context manager).

#### Context Manager

```python
with PayloadInterface(i2c_bus=1) as iface:
    desc = iface.discover()
    if desc:
        iface.ping()
```

---

### Function: `crc16_modbus(data: bytes) -> int`

Compute CRC-16/MODBUS checksum over the input bytes.

**Algorithm:** Polynomial 0xA001 (reflected), initial value 0xFFFF.

```python
from sdk.payload_interface.payload_protocol import crc16_modbus

checksum = crc16_modbus(b"\x01\x03\x00\x00\x00\x01")
```

---

## Module: `payload_interface.capability_flags`

Canonical bit definitions for the capabilities byte in the EEPROM descriptor.

```python
from sdk.payload_interface.capability_flags import (
    CAP_I2C, CAP_SPI, CAP_UART, CAP_GPIO, CAP_ADC, CAP_PWM, CAP_CAN,
    CAPABILITY_NAMES,
)
```

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CAP_I2C` | `0x01` | I2C slave interface |
| `CAP_SPI` | `0x02` | SPI slave interface |
| `CAP_UART` | `0x04` | UART communication |
| `CAP_GPIO` | `0x08` | General-purpose I/O |
| `CAP_ADC` | `0x10` | Analog-to-digital converter |
| `CAP_PWM` | `0x20` | PWM output |
| `CAP_CAN` | `0x40` | CAN bus interface |
| `CAP_RESERVED` | `0x80` | Reserved for future use |

### `CAPABILITY_NAMES: dict[int, str]`

Maps each flag to a human-readable name for display purposes.

---

## Module: `tools.eeprom_validator`

CLI tool for validating and generating EEPROM descriptor binary files.

### Usage

```bash
# Validate an existing binary descriptor
python -m sdk.tools.eeprom_validator validate payload.bin

# Generate a new descriptor binary
python -m sdk.tools.eeprom_validator generate \
    --payload-id "SENSOR_V2" \
    --name "Environmental Monitor" \
    --power-5v 500 \
    --power-12v 0 \
    --capabilities i2c,adc \
    --output payload.bin
```

### Validation Checks

The validator enforces:
- Magic bytes: `b"PBC4"` at offset 0
- Version: `0x01`
- Power budget: 5V rail max 5000mA, 12V rail max 3000mA, total max 50W
- ASCII-only payload_id and name fields
- Capability/GPIO consistency (GPIO mask must be zero if `CAP_GPIO` not set)
- Exactly 64 bytes total size

---

## EEPROM Binary Layout

| Offset | Size | Field |
|--------|------|-------|
| `0x00` | 4 | Magic (`"PBC4"`) |
| `0x04` | 1 | Version (`0x01`) |
| `0x05` | 16 | Payload ID (ASCII, null-padded) |
| `0x15` | 32 | Name (ASCII, null-padded) |
| `0x35` | 2 | Power 5V max (big-endian, mA) |
| `0x37` | 2 | Power 12V max (big-endian, mA) |
| `0x39` | 1 | Capabilities bitmask |
| `0x3A` | 1 | GPIO mask |
| `0x3B` | 1 | I2C address count |
| `0x3C` | 4 | Reserved (zeros) |

Total: 64 bytes.

---

## Command Protocol Reference

Standard command IDs:

| ID | Name | Direction | Description |
|----|------|-----------|-------------|
| `0x01` | PING | Host → Payload | Heartbeat check |
| `0x02` | STATUS | Host → Payload | Request status data |
| `0x03` | CONFIG | Host → Payload | Write configuration |
| `0x04` | DATA | Host → Payload | Data transfer |
| `0x05` | RESET | Host → Payload | Soft reset |
| `0x81` | ACK | Payload → Host | Command acknowledged |
| `0x82` | ERROR | Payload → Host | Command failed |

---

## Complete Example

```python
from sdk.payload_interface.payload_protocol import PayloadInterface
from sdk.payload_interface.capability_flags import CAP_I2C, CAPABILITY_NAMES

with PayloadInterface(i2c_bus=1) as iface:
    desc = iface.discover()
    if desc is None:
        print("No payload detected")
        exit(1)

    print(f"Connected: {desc.name} ({desc.payload_id})")
    print(f"Power: {desc.power_5v_ma}mA @5V, {desc.power_12v_ma}mA @12V")

    # Print capabilities
    for flag, name in CAPABILITY_NAMES.items():
        if desc.capabilities & flag:
            print(f"  - {name}")

    # Communication test
    if iface.ping():
        print("Payload responding to PING")

    status = iface.get_status()
    if status:
        print(f"Status: {status.hex()}")
```
