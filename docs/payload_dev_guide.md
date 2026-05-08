# Payload Development Guide

This guide explains how to design and develop custom payloads for the robot-platform using the PBC-34 connector.

## Overview

The PBC-34 (Payload Bus Connector, 34-pin) provides:
- **Power**: 5V/5A, 12V/3A, VBAT (7.4V)/10A
- **Communication**: I2C, UART, 8× GPIO, USB, CAN (industrial)
- **Control signals**: Enable, Fault, Detect, Interrupt
- **Auto-discovery**: EEPROM-based identification

## Architecture

```
┌─────────────────────────┐
│      Your Payload       │
│                         │
│  ┌───────┐ ┌────────┐  │
│  │Sensors│ │Actuator│  │
│  └───┬───┘ └────┬───┘  │
│      │          │       │
│  ┌───┴──────────┴───┐  │
│  │  Payload MCU     │  │
│  │  (Arduino/STM32) │  │
│  └────────┬─────────┘  │
│           │             │
│  ┌────────┴─────────┐  │
│  │ EEPROM (24C02)   │  │
│  └──────────────────┘  │
└───────────┬─────────────┘
            │ PBC-34
┌───────────┴─────────────┐
│    Robot Platform        │
└──────────────────────────┘
```

## Step 1: Design Payload Hardware

### Minimum Requirements

1. **EEPROM** (24C02 or compatible, I2C address 0x50)
   - Connected to PBC-34 pins 30 (ID SCL) and 31 (ID SDA)
   - Contains payload descriptor (see format below)

2. **DETECT** mechanism
   - Connect PBC-34 pin 27 to GND through a normally-open contact
   - When payload is seated, contact closes, pulling DETECT low

3. **Power decoupling**
   - 100µF + 100nF on each power rail you use
   - Soft-start circuit if inrush current > 500mA

### Recommended

- **FAULT** output (pin 26): Open-drain, pull low to signal error
- **INT** output (pin 28): Open-drain, pull low to request attention
- **I2C** interface for command/response communication

### Power Budget

Before requesting power, verify your total draw fits within:

| Rail | Maximum | Shared with |
|------|---------|-------------|
| 5V | 5A total | Platform sensors (if no isolation) |
| 12V | 3A total | Exclusive to payload |
| VBAT | 10A total | Motors (when moving) |

## Step 2: Program EEPROM

Write the payload descriptor to the first 64 bytes of the EEPROM.

### Using Python (with EEPROM connected to dev machine)

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

# Name (32 bytes, UTF-8, null-terminated)
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

## Step 3: Implement Communication Protocol

Your payload MCU should respond to I2C commands from the platform.

### Arduino Example (I2C Slave)

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
    // Verify frame: [START=0xAA] [LEN] [CMD] [DATA...] [CRC16]
    if (len < 5 || data[0] != 0xAA) return;

    uint8_t cmdLen = data[1];
    uint8_t cmd = data[2];

    switch (cmd) {
        case 0x01: // PING
            txBuffer[0] = 0xAA;
            txBuffer[1] = 1;
            txBuffer[2] = 0x81; // ACK
            // Add CRC...
            txLen = 5;
            break;

        case 0x02: // STATUS
            txBuffer[0] = 0xAA;
            txBuffer[1] = 2;
            txBuffer[2] = 0x81; // ACK
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

## Step 4: Create ROS2 Node

See `sdk/examples/sensor_payload.py` for a complete example of a ROS2 node that reads from a payload and publishes data.

Key steps:
1. Import `PayloadInterface` from `sdk/payload_interface/`
2. Call `discover()` to verify payload presence
3. Create a ROS2 publisher for your data type
4. Periodically send commands and publish responses

## Step 5: Test Hot-Plug

1. Start the robot platform (firmware running, ROS2 active)
2. Insert your payload into the PBC-34 connector
3. Monitor the console for discovery messages
4. Verify in ROS2: `ros2 topic echo /payload/connected`
5. Remove the payload while running — verify graceful disconnect
6. Re-insert — verify re-discovery works

## Design Checklist

- [ ] EEPROM programmed with valid descriptor
- [ ] DETECT pin mechanism works (low when seated)
- [ ] Power draw within rail limits
- [ ] Decoupling capacitors on all power inputs
- [ ] I2C pull-ups present (4.7kΩ to 3.3V)
- [ ] FAULT pin implemented (or left floating with pull-up)
- [ ] Command protocol responses include valid CRC
- [ ] Hot-plug tested (insert/remove under power)
- [ ] No backfeed from payload to platform when platform is off

## Safety Considerations

1. **Never bypass overcurrent protection** — if your payload draws more than rated, redesign it
2. **Implement watchdog** — if your MCU hangs, assert FAULT pin
3. **Isolate high-voltage** — if your payload uses >12V internally, use galvanic isolation
4. **Motor payloads** — actuators must have their own E-stop consideration; platform E-stop should also disable payload motors via ENABLE pin
