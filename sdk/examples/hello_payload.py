#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Minimal payload discovery and communication example."""

import sys
sys.path.insert(0, '..')

from payload_interface.payload_protocol import PayloadInterface


def main():
    print("PBC-34 Payload Discovery Example")
    print("=" * 40)

    interface = PayloadInterface(i2c_bus=1)

    print("Scanning for payload on EEPROM bus...")
    descriptor = interface.discover()

    if descriptor is None:
        print("No payload detected.")
        interface.close()
        return

    print(f"  Payload ID:   {descriptor.payload_id}")
    print(f"  Name:         {descriptor.name}")
    print(f"  Power (5V):   {descriptor.power_5v_ma} mA")
    print(f"  Power (12V):  {descriptor.power_12v_ma} mA")
    print(f"  Interfaces:   ", end="")
    interfaces = []
    if descriptor.uses_i2c:  interfaces.append("I2C")
    if descriptor.uses_uart: interfaces.append("UART")
    if descriptor.uses_gpio: interfaces.append("GPIO")
    if descriptor.uses_usb:  interfaces.append("USB")
    if descriptor.uses_can:  interfaces.append("CAN")
    print(", ".join(interfaces) or "None")

    print("\nSending PING...")
    if interface.ping():
        print("  Payload responded: OK")
    else:
        print("  No response from payload")

    print("\nRequesting status...")
    status = interface.get_status()
    if status:
        print(f"  Raw status: {status.hex()}")
    else:
        print("  No status response")

    interface.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
