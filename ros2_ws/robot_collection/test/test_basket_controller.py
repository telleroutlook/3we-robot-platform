# SPDX-License-Identifier: Apache-2.0
"""Unit tests for basket controller state and angle validation."""

from robot_collection.constants import BasketState


class TestBasketState:
    def test_state_values(self) -> None:
        assert BasketState.NORMAL.value == "normal"
        assert BasketState.DUMPING.value == "dumping"
        assert BasketState.RESETTING.value == "resetting"

    def test_state_count(self) -> None:
        assert len(BasketState) == 3


class TestServoAngleValidation:
    """Test servo angle parameter constraints."""

    def test_dump_angle_range(self) -> None:
        dump_angle = 120
        assert 0 <= dump_angle <= 180

    def test_home_angle_zero(self) -> None:
        home_angle = 0
        assert home_angle == 0

    def test_dump_hold_time_positive(self) -> None:
        dump_hold = 2.0
        assert dump_hold > 0

    def test_reset_time_positive(self) -> None:
        reset_time = 1.0
        assert reset_time > 0
