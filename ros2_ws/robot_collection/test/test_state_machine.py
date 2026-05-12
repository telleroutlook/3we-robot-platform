# SPDX-License-Identifier: Apache-2.0
"""Unit tests for CollectionStage constants and state machine logic."""

import pytest

from robot_collection.constants import CollectionStage


class TestCollectionStage:
    def test_stage_enum_values(self) -> None:
        assert CollectionStage.IDLE == 0
        assert CollectionStage.SEARCHING == 1
        assert CollectionStage.APPROACHING == 2
        assert CollectionStage.PICKING == 3
        assert CollectionStage.RETURNING == 4
        assert CollectionStage.DUMPING == 5

    def test_stage_count(self) -> None:
        assert len(CollectionStage) == 6

    def test_stage_names(self) -> None:
        assert CollectionStage.IDLE.name == "IDLE"
        assert CollectionStage.SEARCHING.name == "SEARCHING"
        assert CollectionStage.APPROACHING.name == "APPROACHING"
        assert CollectionStage.PICKING.name == "PICKING"
        assert CollectionStage.RETURNING.name == "RETURNING"
        assert CollectionStage.DUMPING.name == "DUMPING"

    def test_stage_int_conversion(self) -> None:
        assert int(CollectionStage.IDLE) == 0
        assert int(CollectionStage.DUMPING) == 5

    def test_stage_from_int(self) -> None:
        assert CollectionStage(0) == CollectionStage.IDLE
        assert CollectionStage(5) == CollectionStage.DUMPING

    def test_stage_ordering(self) -> None:
        stages = list(CollectionStage)
        for i in range(len(stages) - 1):
            assert stages[i] < stages[i + 1]

    def test_invalid_stage_raises(self) -> None:
        with pytest.raises(ValueError):
            CollectionStage(99)
