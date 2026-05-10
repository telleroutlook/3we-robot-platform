# SPDX-License-Identifier: Apache-2.0
"""Docking stage constants — importable without ROS2 dependencies."""

from enum import IntEnum


class DockingStage(IntEnum):
    IDLE = 0
    APPROACH = 1
    VISUAL_SERVO_COARSE = 2
    VISUAL_SERVO_FINE = 3
    CONTACT_VERIFY = 4
    DOCKED = 5
    UNDOCKING = 6
    FAILED = 7
