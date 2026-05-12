# SPDX-License-Identifier: Apache-2.0
"""PBC-34 Payload Capability Flags — canonical bit definitions.

All tools (payload_protocol, eeprom_validator) must import from here
to avoid bit definition drift.
"""

CAP_I2C = 0x01
CAP_SPI = 0x02
CAP_UART = 0x04
CAP_GPIO = 0x08
CAP_ADC = 0x10
CAP_PWM = 0x20
CAP_CAN = 0x40
CAP_CAMERA = 0x80

CAPABILITY_NAMES = {
    CAP_I2C: "I2C Slave",
    CAP_SPI: "SPI Slave",
    CAP_UART: "UART",
    CAP_GPIO: "GPIO",
    CAP_ADC: "ADC",
    CAP_PWM: "PWM",
    CAP_CAN: "CAN",
    CAP_CAMERA: "Camera",
}
