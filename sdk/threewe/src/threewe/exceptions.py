# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for threewe.

All exceptions inherit from ThreeweError to allow blanket catching.
"""


class ThreeweError(Exception):
    """Base exception for all threewe errors."""


class RobotConnectionError(ThreeweError):
    """Cannot connect to the robot or simulator."""


class NavigationError(ThreeweError):
    """Navigation action failed (path blocked, goal unreachable)."""


class HardwareError(ThreeweError):
    """Hardware fault detected (motor overheat, sensor disconnect)."""


class EmergencyStopError(ThreeweError):
    """Emergency stop triggered."""


class RobotTimeoutError(ThreeweError):
    """Operation timed out."""


class SafetyError(ThreeweError):
    """Safety constraint violated (speed limit, boundary breach)."""


# Aliases for backwards-compatibility and shorter import names
ConnectionError = RobotConnectionError
TimeoutError = RobotTimeoutError
