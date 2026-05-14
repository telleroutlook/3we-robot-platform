# SPDX-License-Identifier: Apache-2.0
"""Tests for exception hierarchy."""

from threewe.exceptions import (
    EmergencyStopError,
    HardwareError,
    NavigationError,
    RobotConnectionError,
    RobotTimeoutError,
    SafetyError,
    ThreeweError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        assert issubclass(RobotConnectionError, ThreeweError)
        assert issubclass(NavigationError, ThreeweError)
        assert issubclass(HardwareError, ThreeweError)
        assert issubclass(EmergencyStopError, ThreeweError)
        assert issubclass(RobotTimeoutError, ThreeweError)
        assert issubclass(SafetyError, ThreeweError)

    def test_can_catch_with_base(self):
        try:
            raise NavigationError("path blocked")
        except ThreeweError as e:
            assert "path blocked" in str(e)

    def test_message_preserved(self):
        err = EmergencyStopError("physical button pressed")
        assert str(err) == "physical button pressed"
