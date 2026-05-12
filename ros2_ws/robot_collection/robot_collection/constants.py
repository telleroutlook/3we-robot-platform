# SPDX-License-Identifier: Apache-2.0
"""Collection constants — importable without ROS2 dependencies."""

from enum import Enum, IntEnum


class CollectionStage(IntEnum):
    IDLE = 0
    SEARCHING = 1
    APPROACHING = 2
    PICKING = 3
    RETURNING = 4
    DUMPING = 5


class ArmState(Enum):
    IDLE = "idle"
    MOVING = "moving"
    HOLDING = "holding"
    ERROR = "error"


class BasketState(Enum):
    NORMAL = "normal"
    DUMPING = "dumping"
    RESETTING = "resetting"
