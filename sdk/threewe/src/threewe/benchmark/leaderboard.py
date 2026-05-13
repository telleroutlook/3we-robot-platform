# SPDX-License-Identifier: Apache-2.0
"""Benchmark leaderboard — submission schema and ranking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeaderboardEntry:
    """A single leaderboard submission entry."""

    agent_name: str
    task: str
    scene: str
    success_rate: float
    spl: float
    hardware: str
    timestamp: str


SUBMISSION_SCHEMA: dict[str, type | str] = {
    "agent_name": str,
    "task": str,
    "scene": str,
    "success_rate": float,
    "spl": float,
    "hardware": str,
    "timestamp": str,
}

_VALID_TASKS = ("pointnav", "objectnav", "exploration")


def validate_submission(data: dict) -> list[str]:
    """Validate a leaderboard submission dict.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []

    for key, expected_type in SUBMISSION_SCHEMA.items():
        if key not in data:
            errors.append(f"Missing required field: '{key}'")
        elif not isinstance(data[key], expected_type):
            errors.append(
                f"Field '{key}' must be {expected_type.__name__}, got {type(data[key]).__name__}"
            )

    if "task" in data and data["task"] not in _VALID_TASKS:
        errors.append(f"Invalid task: '{data['task']}'. Must be one of: {_VALID_TASKS}")

    if "success_rate" in data and isinstance(data["success_rate"], (int, float)):
        if not (0.0 <= data["success_rate"] <= 1.0):
            errors.append("success_rate must be between 0.0 and 1.0")

    if "spl" in data and isinstance(data["spl"], (int, float)):
        if not (0.0 <= data["spl"] <= 1.0):
            errors.append("spl must be between 0.0 and 1.0")

    return errors


def rank_entries(entries: list[LeaderboardEntry], metric: str = "spl") -> list[LeaderboardEntry]:
    """Rank leaderboard entries by a given metric (descending).

    Args:
        entries: List of entries to rank.
        metric: Metric to sort by ("spl", "success_rate").

    Returns:
        Sorted list from best to worst.
    """
    if metric not in ("spl", "success_rate"):
        raise ValueError(f"Invalid metric: '{metric}'. Choose from: 'spl', 'success_rate'")

    return sorted(entries, key=lambda e: getattr(e, metric), reverse=True)
