# PBC-34 Payload Interface

Python library for communicating with PBC-34 payload devices via I2C.

For the complete reference (hardware design, EEPROM format, communication protocol, examples), see [docs/pbc34_payload_guide.md](../../docs/pbc34_payload_guide.md).

## Quick Start

```python
from sdk.payload_interface.payload_protocol import PayloadInterface

with PayloadInterface(i2c_bus=1) as iface:
    desc = iface.discover()
    if desc:
        print(f"Found: {desc.name} (ID: {desc.payload_id})")
        iface.ping()
```

## Installation

```bash
pip install smbus2
```
