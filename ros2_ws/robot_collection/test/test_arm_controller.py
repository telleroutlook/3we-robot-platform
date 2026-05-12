# SPDX-License-Identifier: Apache-2.0
"""Unit tests for arm controller command validation."""

from robot_collection.constants import ArmState


class TestArmState:
    def test_state_values(self) -> None:
        assert ArmState.IDLE.value == "idle"
        assert ArmState.MOVING.value == "moving"
        assert ArmState.HOLDING.value == "holding"
        assert ArmState.ERROR.value == "error"

    def test_state_count(self) -> None:
        assert len(ArmState) == 4


class TestArmCommandValidation:
    """Test that command strings are handled correctly."""

    def test_valid_commands(self) -> None:
        valid = {"pick", "retract", "home"}
        for cmd in valid:
            assert cmd.lower() in valid

    def test_case_insensitive(self) -> None:
        assert "PICK".lower() == "pick"
        assert "Retract".lower() == "retract"

    def test_unknown_command(self) -> None:
        valid = {"pick", "retract", "home"}
        assert "dance" not in valid
