# SPDX-License-Identifier: Apache-2.0
"""Tests for payload_interface.capability_flags module."""

from payload_interface.capability_flags import (
    CAP_ADC,
    CAP_CAMERA,
    CAP_CAN,
    CAP_GPIO,
    CAP_I2C,
    CAP_PWM,
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
    CAP_CAMERA,
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


def test_capability_names_covers_all_flags():
    for flag in ALL_FLAGS:
        assert flag in CAPABILITY_NAMES


def test_camera_is_highest_bit():
    assert CAP_CAMERA == 0x80
    for flag in ALL_FLAGS:
        if flag != CAP_CAMERA:
            assert flag < CAP_CAMERA


def test_flag_values_ascending():
    for i in range(len(ALL_FLAGS) - 1):
        assert ALL_FLAGS[i] < ALL_FLAGS[i + 1]
