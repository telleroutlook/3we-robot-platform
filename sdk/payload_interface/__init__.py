# SPDX-License-Identifier: Apache-2.0
"""PBC-34 Payload Interface SDK."""

__all__ = [
    "PayloadInterface",
    "PayloadDescriptor",
    "crc16_modbus",
    "CAP_I2C",
    "CAP_SPI",
    "CAP_UART",
    "CAP_GPIO",
    "CAP_ADC",
    "CAP_PWM",
    "CAP_CAN",
    "AsyncPayloadClient",
    "MissionResult",
    "BatteryState",
    "PayloadState",
]

from .capability_flags import (
    CAP_ADC as CAP_ADC,
    CAP_CAN as CAP_CAN,
    CAP_GPIO as CAP_GPIO,
    CAP_I2C as CAP_I2C,
    CAP_PWM as CAP_PWM,
    CAP_SPI as CAP_SPI,
    CAP_UART as CAP_UART,
)
from .payload_protocol import (
    PayloadDescriptor as PayloadDescriptor,
    PayloadInterface as PayloadInterface,
    crc16_modbus as crc16_modbus,
)

try:
    from .async_client import (
        AsyncPayloadClient as AsyncPayloadClient,
        BatteryState as BatteryState,
        MissionResult as MissionResult,
        PayloadState as PayloadState,
    )
except ImportError:
    pass
