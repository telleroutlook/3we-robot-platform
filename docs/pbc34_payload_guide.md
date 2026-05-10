# PBC-34 Payload Interface — Complete Reference

The Payload Bus Connector (PBC-34) is a standardized 34-pin interface for attaching modular payloads to the robot platform. It provides power, communication, and control signals through a single hot-pluggable connector.

## Overview

- Hot-plug with automatic discovery (EEPROM-based)
- Multiple power rails (5V, 12V, VBAT)
- I2C, UART, GPIO, USB, CAN communication channels
- Hardware fault detection and isolation
- Software-controlled power sequencing

## Pin Map

See `hardware/pcb/README.md` for the complete 34-pin assignment table.

### Key Pins

| Pin | Name | Description |
|-----|------|-------------|
| 26 | FAULT | Open-drain, payload pulls low to signal error |
| 27 | DETECT | Pulled low when payload is physically seated |
| 28 | INT | Open-drain, payload pulls low to request attention |
| 30 | ID SCL | EEPROM I2C clock |
| 31 | ID SDA | EEPROM I2C data |

---

## Hardware Design

### Minimum Requirements

1. **EEPROM** (24C02 or compatible, I2C address 0x50)
   - Connected to PBC-34 pins 30 (ID SCL) and 31 (ID SDA)
   - Contains payload descriptor (see EEPROM section below)

2. **DETECT** mechanism
   - Connect PBC-34 pin 27 to GND through a normally-open contact
   - When payload is seated, contact closes, pulling DETECT low

3. **Power decoupling**
   - 100uF + 100nF on each power rail you use
   - Soft-start circuit if inrush current > 500mA

### Power Budget

| Rail | Maximum | Notes |
|------|---------|-------|
| 5V | 5A (5000mA) | Shared with platform sensors (if no isolation) |
| 12V | 3A (3000mA) | Exclusive to payload |
| VBAT | 10A | Shared with motors (when moving) |
| Total | 50W max | Across all rails combined |

### Safety Interlocks

- **Overcurrent**: If a rail exceeds rated current by 20%, the rail is disabled within 1ms
- **Thermal**: If junction temperature exceeds 85C, all rails are disabled
- **Fault feedback**: Payload asserts FAULT pin (26) to signal internal error
- **Platform response**: Disable power rails, publish `/payload/fault` event

---

## EEPROM Descriptor Format

Each payload carries a 256-byte I2C EEPROM (address 0x50) on the ID bus. The first 64 bytes contain the payload descriptor:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| `0x00` | 4 | Magic | `"PBC4"` (`0x50 0x42 0x43 0x34`) |
| `0x04` | 1 | Version | Descriptor format version (`0x01`) |
| `0x05` | 16 | Payload ID | Unique identifier (ASCII, null-padded) |
| `0x15` | 32 | Name | Human-readable name (ASCII, null-padded) |
| `0x35` | 2 | Power 5V (mA) | Maximum 5V current draw (uint16, big-endian) |
| `0x37` | 2 | Power 12V (mA) | Maximum 12V current draw (uint16, big-endian) |
| `0x39` | 1 | Capabilities | Bitfield (see below) |
| `0x3A` | 1 | GPIO mask | Which of the 8 GPIOs this payload uses |
| `0x3B` | 1 | I2C addresses | Number of I2C addresses used |
| `0x3C` | 4 | Reserved | Future use (set to `0x00`) |

Total: 64 bytes.

### Capabilities Bitfield

| Bit | Flag | Value | Interface |
|-----|------|-------|-----------|
| 0 | `CAP_I2C` | `0x01` | I2C slave interface |
| 1 | `CAP_SPI` | `0x02` | SPI slave interface |
| 2 | `CAP_UART` | `0x04` | UART communication |
| 3 | `CAP_GPIO` | `0x08` | General-purpose I/O |
| 4 | `CAP_ADC` | `0x10` | Analog-to-digital converter |
| 5 | `CAP_PWM` | `0x20` | PWM output |
| 6 | `CAP_CAN` | `0x40` | CAN bus interface |
| 7 | `CAP_RESERVED` | `0x80` | Reserved for future use |

---

## Communication Protocol

Commands are sent over I2C (address configurable per payload, default `0x10`).

### Frame Format

```
[START] [LENGTH] [CMD_ID] [DATA...] [CRC16_H] [CRC16_L]
```

| Field | Size | Description |
|-------|------|-------------|
| START | 1 | Always `0xAA` |
| LENGTH | 1 | Byte count of CMD_ID + DATA (excluding CRC) |
| CMD_ID | 1 | Command identifier |
| DATA | 0-252 | Command-specific data |
| CRC16 | 2 | CRC-16/MODBUS over LENGTH + CMD_ID + DATA |

**CRC algorithm**: Polynomial 0xA001 (reflected), initial value 0xFFFF.

### Standard Commands

| CMD_ID | Name | Direction | Description |
|--------|------|-----------|-------------|
| `0x01` | PING | Host -> Payload | Heartbeat check |
| `0x02` | STATUS | Host -> Payload | Request status data |
| `0x03` | CONFIG | Host -> Payload | Write configuration |
| `0x04` | DATA | Host -> Payload | Data transfer |
| `0x05` | RESET | Host -> Payload | Soft reset |
| `0x81` | ACK | Payload -> Host | Command acknowledged |
| `0x82` | ERROR | Payload -> Host | Command failed |

---

## Hot-Plug Sequence

1. **T+0ms**: Payload physically inserted, DETECT pin (27) goes low
2. **T+10ms**: Debounce confirmation
3. **T+20ms**: Read EEPROM descriptor (pins 30-31)
4. **T+30ms**: Verify power budget (total current < rail capacity)
5. **T+40ms**: Enable 3.3V logic reference
6. **T+50ms**: Enable 5V rail (10ms soft-start ramp)
7. **T+70ms**: Enable 12V rail (10ms soft-start ramp)
8. **T+90ms**: Wait for payload initialization (monitor FAULT pin)
9. **T+200ms**: Payload ready, publish ROS2 `/payload/connected`
10. **T+300ms**: Communication channels activated

---

## Python SDK Reference

### Installation

```bash
pip install smbus2
```

### Class: `PayloadDescriptor`

Frozen dataclass representing a parsed EEPROM payload descriptor.

```python
from sdk.payload_interface.payload_protocol import PayloadDescriptor
```

| Field | Type | Description |
|-------|------|-------------|
| `payload_id` | `str` | Unique identifier (max 16 chars, ASCII) |
| `name` | `str` | Human-readable name (max 32 chars, ASCII) |
| `power_5v_ma` | `int` | Maximum 5V rail current draw in milliamps |
| `power_12v_ma` | `int` | Maximum 12V rail current draw in milliamps |
| `capabilities` | `int` | Bitmask of capability flags |
| `gpio_mask` | `int` | Bitmask of used GPIO pins |
| `i2c_addr_count` | `int` | Number of additional I2C addresses used |

Properties: `uses_i2c`, `uses_spi`, `uses_uart`, `uses_gpio`, `uses_can`.

#### `from_eeprom(data: bytes) -> Optional[PayloadDescriptor]`

Parse raw EEPROM data (minimum 64 bytes). Returns `None` if magic/version is invalid.

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

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `discover()` | `Optional[PayloadDescriptor]` | Read EEPROM and parse descriptor |
| `send_command(cmd_id, data, timeout_ms)` | `Optional[bytes]` | Send framed command, read response |
| `ping()` | `bool` | Send PING, return True if ACK received |
| `get_status()` | `Optional[bytes]` | Send STATUS command |
| `reset()` | `bool` | Send RESET command |
| `close()` | `None` | Close I2C bus handle |

Supports context manager (`with PayloadInterface() as iface:`).

### Function: `crc16_modbus(data: bytes) -> int`

Compute CRC-16/MODBUS checksum. Polynomial 0xA001, initial 0xFFFF.

### EEPROM Validator Tool

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

---

## Implementation Examples

### Programming the EEPROM (Python)

```python
import struct
import smbus2

bus = smbus2.SMBus(1)
EEPROM_ADDR = 0x50

descriptor = bytearray(64)

# Magic header
descriptor[0:4] = b'PBC4'

# Version
descriptor[4] = 0x01

# Payload ID (16 bytes, null-padded)
payload_id = b'my-sensor-v1'
descriptor[5:5+len(payload_id)] = payload_id

# Name (32 bytes, null-terminated)
name = 'Temperature Sensor'.encode('utf-8')
descriptor[0x15:0x15+len(name)] = name

# Power requirements (big-endian uint16)
struct.pack_into('>H', descriptor, 0x35, 200)   # 5V: 200mA
struct.pack_into('>H', descriptor, 0x37, 0)     # 12V: 0mA

# Capabilities: I2C only
descriptor[0x39] = 0x01

# GPIO mask: none
descriptor[0x3A] = 0x00

# I2C addresses used: 1
descriptor[0x3B] = 1

# Write to EEPROM (page-write, 8 bytes at a time)
for offset in range(0, 64, 8):
    page = list(descriptor[offset:offset+8])
    bus.write_i2c_block_data(EEPROM_ADDR, offset, page)
    import time; time.sleep(0.01)  # EEPROM write cycle

print("EEPROM programmed successfully")
bus.close()
```

### Arduino I2C Slave (Payload MCU)

```cpp
#include <Wire.h>

#define PAYLOAD_I2C_ADDR 0x10

uint8_t rxBuffer[32];
uint8_t txBuffer[32];
uint8_t txLen = 0;

void setup() {
    Wire.begin(PAYLOAD_I2C_ADDR);
    Wire.onReceive(onReceive);
    Wire.onRequest(onRequest);
}

void onReceive(int numBytes) {
    int i = 0;
    while (Wire.available() && i < 32) {
        rxBuffer[i++] = Wire.read();
    }
    processCommand(rxBuffer, i);
}

void onRequest() {
    Wire.write(txBuffer, txLen);
    txLen = 0;
}

void processCommand(uint8_t *data, int len) {
    if (len < 5 || data[0] != 0xAA) return;

    uint8_t cmd = data[2];

    switch (cmd) {
        case 0x01: // PING
            txBuffer[0] = 0xAA;
            txBuffer[1] = 1;
            txBuffer[2] = 0x81; // ACK
            txLen = 5;
            break;

        case 0x02: // STATUS
            txBuffer[0] = 0xAA;
            txBuffer[1] = 2;
            txBuffer[2] = 0x81;
            txBuffer[3] = 0x01; // Status: active
            txLen = 6;
            break;

        case 0x10: // READ_TEMPERATURE (custom)
            float temp = readTemperature();
            txBuffer[0] = 0xAA;
            txBuffer[1] = 3;
            txBuffer[2] = 0x81;
            txBuffer[3] = (uint8_t)temp;
            txBuffer[4] = (uint8_t)((temp - (int)temp) * 100);
            txLen = 7;
            break;
    }
}

void loop() {
    delay(10);
}
```

### Complete Python Host Example

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

    for flag, name in CAPABILITY_NAMES.items():
        if desc.capabilities & flag:
            print(f"  - {name}")

    if iface.ping():
        print("Payload responding to PING")

    status = iface.get_status()
    if status:
        print(f"Status: {status.hex()}")
```

---

## ROS2 Integration

See `sdk/examples/sensor_payload.py` for a complete ROS2 node example.

Key steps:
1. Import `PayloadInterface` from `sdk/payload_interface/`
2. Call `discover()` to verify payload presence
3. Create a ROS2 publisher for your data type
4. Periodically send commands and publish responses

---

## Testing Hot-Plug

1. Start the robot platform (firmware running, ROS2 active)
2. Insert your payload into the PBC-34 connector
3. Monitor the console for discovery messages
4. Verify in ROS2: `ros2 topic echo /payload/connected`
5. Remove the payload while running — verify graceful disconnect
6. Re-insert — verify re-discovery works

---

## Design Checklist

- [ ] EEPROM programmed with valid descriptor
- [ ] DETECT pin mechanism works (low when seated)
- [ ] Power draw within rail limits
- [ ] Decoupling capacitors on all power inputs
- [ ] I2C pull-ups present (4.7k to 3.3V)
- [ ] FAULT pin implemented (or left floating with pull-up)
- [ ] Command protocol responses include valid CRC
- [ ] Hot-plug tested (insert/remove under power)
- [ ] No backfeed from payload to platform when platform is off

## Safety Considerations

1. **Never bypass overcurrent protection** — if your payload draws more than rated, redesign it
2. **Implement watchdog** — if your MCU hangs, assert FAULT pin
3. **Isolate high-voltage** — if your payload uses >12V internally, use galvanic isolation
4. **Motor payloads** — actuators must have their own E-stop consideration; platform E-stop should also disable payload motors via ENABLE pin
