# SPDX-License-Identifier: Apache-2.0
"""Tests for benchmark leaderboard."""

from __future__ import annotations

import pytest

from threewe.benchmark.leaderboard import (
    LeaderboardEntry,
    rank_entries,
    validate_submission,
)


class TestLeaderboardEntry:
    def test_creation(self):
        entry = LeaderboardEntry(
            agent_name="my_agent",
            task="pointnav",
            scene="office_v2",
            success_rate=0.85,
            spl=0.72,
            hardware="3we_standard_v2",
            timestamp="2026-05-13T10:00:00",
        )
        assert entry.agent_name == "my_agent"
        assert entry.spl == 0.72

    def test_frozen(self):
        entry = LeaderboardEntry(
            agent_name="a",
            task="pointnav",
            scene="s",
            success_rate=0.5,
            spl=0.4,
            hardware="h",
            timestamp="t",
        )
        with pytest.raises(AttributeError):
            entry.spl = 0.9  # type: ignore[misc]


class TestValidateSubmission:
    def test_valid_submission(self):
        data = {
            "agent_name": "my_agent",
            "task": "pointnav",
            "scene": "office_v2",
            "success_rate": 0.85,
            "spl": 0.72,
            "hardware": "3we_standard_v2",
            "timestamp": "2026-05-13T10:00:00",
        }
        errors = validate_submission(data)
        assert errors == []

    def test_missing_fields(self):
        data = {"agent_name": "my_agent"}
        errors = validate_submission(data)
        assert len(errors) >= 5

    def test_invalid_task(self):
        data = {
            "agent_name": "a",
            "task": "invalid_task",
            "scene": "s",
            "success_rate": 0.5,
            "spl": 0.4,
            "hardware": "h",
            "timestamp": "t",
        }
        errors = validate_submission(data)
        assert any("Invalid task" in e for e in errors)

    def test_success_rate_out_of_range(self):
        data = {
            "agent_name": "a",
            "task": "pointnav",
            "scene": "s",
            "success_rate": 1.5,
            "spl": 0.4,
            "hardware": "h",
            "timestamp": "t",
        }
        errors = validate_submission(data)
        assert any("success_rate" in e for e in errors)

    def test_spl_out_of_range(self):
        data = {
            "agent_name": "a",
            "task": "pointnav",
            "scene": "s",
            "success_rate": 0.5,
            "spl": -0.1,
            "hardware": "h",
            "timestamp": "t",
        }
        errors = validate_submission(data)
        assert any("spl" in e for e in errors)

    def test_wrong_type(self):
        data = {
            "agent_name": 123,
            "task": "pointnav",
            "scene": "s",
            "success_rate": 0.5,
            "spl": 0.4,
            "hardware": "h",
            "timestamp": "t",
        }
        errors = validate_submission(data)
        assert any("agent_name" in e for e in errors)


class TestRankEntries:
    def test_rank_by_spl(self):
        entries = [
            LeaderboardEntry("a", "pointnav", "s", 0.8, 0.5, "h", "t"),
            LeaderboardEntry("b", "pointnav", "s", 0.9, 0.9, "h", "t"),
            LeaderboardEntry("c", "pointnav", "s", 0.7, 0.7, "h", "t"),
        ]
        ranked = rank_entries(entries, metric="spl")
        assert ranked[0].agent_name == "b"
        assert ranked[1].agent_name == "c"
        assert ranked[2].agent_name == "a"

    def test_rank_by_success_rate(self):
        entries = [
            LeaderboardEntry("a", "pointnav", "s", 0.6, 0.5, "h", "t"),
            LeaderboardEntry("b", "pointnav", "s", 0.9, 0.4, "h", "t"),
            LeaderboardEntry("c", "pointnav", "s", 0.8, 0.7, "h", "t"),
        ]
        ranked = rank_entries(entries, metric="success_rate")
        assert ranked[0].agent_name == "b"
        assert ranked[1].agent_name == "c"
        assert ranked[2].agent_name == "a"

    def test_invalid_metric_raises(self):
        with pytest.raises(ValueError, match="Invalid metric"):
            rank_entries([], metric="invalid")

    def test_empty_list(self):
        ranked = rank_entries([], metric="spl")
        assert ranked == []
