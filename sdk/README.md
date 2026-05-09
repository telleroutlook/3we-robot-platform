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
from payload_interface import PayloadProtocol

protocol = PayloadProtocol(bus=1, address=0x50)
protocol.read_capability_flags()
```

## License

Apache-2.0
