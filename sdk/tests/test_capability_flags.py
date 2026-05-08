# SPDX-License-Identifier: Apache-2.0
"""Tests for payload_interface.capability_flags module."""

from payload_interface.capability_flags import (
    CAP_ADC,
    CAP_CAN,
    CAP_GPIO,
    CAP_I2C,
    CAP_PWM,
    CAP_RESERVED,
    CAP_SPI,
    CAP_UART,
    CAPABILITY_NAMES,
)

ALL_FLAGS = [
    CAP_I2C,
    CAP_SPI,
    CAP_UART,
    CAP_GPIO,
    CAP_ADC,
    CAP_PWM,
    CAP_CAN,
    CAP_RESERVED,
]


def test_all_flags_are_single_bits():
    for flag in ALL_FLAGS:
        assert flag > 0
        assert (flag & (flag - 1)) == 0, f"Flag 0x{flag:02X} is not a power of 2"


def test_no_flag_overlap():
    combined = 0
    for flag in ALL_FLAGS:
        assert (combined & flag) == 0, f"Flag 0x{flag:02X} overlaps with previous flags"
        combined |= flag


def test_capability_names_covers_all_non_reserved():
    for flag in ALL_FLAGS:
        if flag == CAP_RESERVED:
            assert flag not in CAPABILITY_NAMES
        else:
            assert flag in CAPABILITY_NAMES


def test_reserved_is_highest_bit():
    assert CAP_RESERVED == 0x80
    for flag in ALL_FLAGS:
        if flag != CAP_RESERVED:
            assert flag < CAP_RESERVED


def test_flag_values_ascending():
    non_reserved = [f for f in ALL_FLAGS if f != CAP_RESERVED]
    for i in range(len(non_reserved) - 1):
        assert non_reserved[i] < non_reserved[i + 1]
