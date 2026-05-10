# SPDX-License-Identifier: Apache-2.0
"""Unit tests for robot_docking state machine logic."""

from robot_docking.constants import DockingStage


class TestDockingStage:
    def test_stage_enum_values(self) -> None:
        assert DockingStage.IDLE == 0
        assert DockingStage.APPROACH == 1
        assert DockingStage.VISUAL_SERVO_COARSE == 2
        assert DockingStage.VISUAL_SERVO_FINE == 3
        assert DockingStage.CONTACT_VERIFY == 4
        assert DockingStage.DOCKED == 5
        assert DockingStage.UNDOCKING == 6
        assert DockingStage.FAILED == 7

    def test_stage_count(self) -> None:
        assert len(DockingStage) == 8

    def test_stage_ordering(self) -> None:
        assert DockingStage.APPROACH < DockingStage.VISUAL_SERVO_COARSE
        assert DockingStage.VISUAL_SERVO_COARSE < DockingStage.VISUAL_SERVO_FINE
        assert DockingStage.VISUAL_SERVO_FINE < DockingStage.CONTACT_VERIFY
        assert DockingStage.CONTACT_VERIFY < DockingStage.DOCKED
