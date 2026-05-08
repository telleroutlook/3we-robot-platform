# PBC-34 Payload Interface

The Payload Bus Connector (PBC-34) is a standardized 34-pin interface for attaching modular payloads to the robot platform. It provides power, communication, and control signals through a single hot-pluggable connector.

## Features

- Hot-plug with automatic discovery (EEPROM-based)
- Multiple power rails (5V, 12V, VBAT)
- I2C, UART, GPIO, USB communication channels
- Hardware fault detection and isolation
- Software-controlled power sequencing

## Pin Map

See `hardware/pcb/README.md` for the complete 34-pin assignment table.

## EEPROM Descriptor Format

Each payload carries a 256-byte I2C EEPROM (address 0x50) on the ID bus (pins 30-31). The first 64 bytes contain the payload descriptor:

| Offset | Length | Field | Description |
|--------|--------|-------|-------------|
| 0x00 | 4 | Magic | `0x50 0x42 0x43 0x34` ("PBC4") |
| 0x04 | 1 | Version | Descriptor format version (currently 0x01) |
| 0x05 | 16 | Payload ID | Unique identifier (UUID, null-padded) |
| 0x15 | 32 | Name | Human-readable name (UTF-8, null-terminated) |
| 0x35 | 2 | Power 5V (mA) | Maximum 5V current draw (uint16, big-endian) |
| 0x37 | 2 | Power 12V (mA) | Maximum 12V current draw (uint16, big-endian) |
| 0x39 | 1 | Capabilities | Bitfield: I2C, UART, GPIO, USB, CAN |
| 0x3A | 1 | GPIO mask | Which of the 8 GPIOs this payload uses |
| 0x3B | 1 | I2C addresses | Number of I2C addresses used |
| 0x3C | 4 | Reserved | Future use (set to 0x00) |

### Capabilities Bitfield

| Bit | Interface |
|-----|-----------|
| 0 | I2C |
| 1 | UART |
| 2 | GPIO |
| 3 | USB |
| 4 | CAN |
| 5-7 | Reserved |

## Communication Protocol

Commands are sent over I2C (address configurable per payload, default 0x10):

```
Frame: [START] [LENGTH] [CMD_ID] [DATA...] [CRC16_H] [CRC16_L]
```

| Field | Size | Description |
|-------|------|-------------|
| START | 1 | Always 0xAA |
| LENGTH | 1 | Payload bytes (CMD_ID + DATA), excluding CRC |
| CMD_ID | 1 | Command identifier |
| DATA | 0-252 | Command-specific data |
| CRC16 | 2 | CRC-16/MODBUS over LENGTH + CMD_ID + DATA |

### Standard Commands

| CMD_ID | Name | Direction | Description |
|--------|------|-----------|-------------|
| 0x01 | PING | Platform → Payload | Heartbeat check |
| 0x02 | STATUS | Platform → Payload | Request status |
| 0x03 | CONFIG | Platform → Payload | Set configuration |
| 0x04 | DATA | Payload → Platform | Sensor/status data |
| 0x05 | RESET | Platform → Payload | Soft reset |
| 0x81 | ACK | Both | Acknowledge receipt |
| 0xFF | ERROR | Both | Error notification |

## Hot-Plug Sequence

1. **T+0ms**: Payload physically inserted → DETECT pin (27) goes low
2. **T+10ms**: Debounce confirmation
3. **T+20ms**: Read EEPROM descriptor (pins 30-31)
4. **T+30ms**: Verify power budget (total current < rail capacity)
5. **T+40ms**: Enable 3.3V logic reference
6. **T+50ms**: Enable 5V rail (10ms soft-start ramp)
7. **T+70ms**: Enable 12V rail (10ms soft-start ramp)
8. **T+90ms**: Wait for payload initialization (monitor FAULT pin)
9. **T+200ms**: Payload ready → publish ROS2 `/payload/connected`
10. **T+300ms**: Communication channels activated

## Usage

```python
from payload_protocol import PayloadInterface

interface = PayloadInterface('/dev/i2c-1')
payload = interface.discover()
if payload:
    print(f"Found: {payload.name} (ID: {payload.payload_id})")
    interface.power_on()
    response = interface.send_command(0x02)  # STATUS
    print(f"Status: {response}")
```

## Safety Interlocks

- Overcurrent: If a rail exceeds rated current by 20%, the rail is disabled within 1ms
- Thermal: If junction temperature exceeds 85°C, all rails are disabled
- Fault feedback: Payload asserts FAULT pin (26) to signal internal error
- Platform response: Disable power rails, publish `/payload/fault` event
