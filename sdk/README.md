# Robot Payload SDK

Python SDK for the PBC-34 Payload Interface on the 3WE Robot Platform.

## Installation

```bash
pip install robot-payload-sdk
```

For development:

```bash
pip install -e ".[dev]"
```

## Packages

- **payload_interface** — Communication library for the standardized payload bus connector
- **tools** — CLI utilities (EEPROM validator, key provisioning)

## Usage

```python
from payload_interface import PayloadInterface

iface = PayloadInterface(i2c_bus=1, eeprom_addr=0x50)
descriptor = iface.discover()
if descriptor:
    print(f"Payload: {descriptor.name} ({descriptor.payload_id})")
```

## License

Apache-2.0
