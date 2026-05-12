# SPDX-License-Identifier: Apache-2.0
"""Benchmark metrics: SPL, Success Rate, Coverage."""

from __future__ import annotations


def compute_spl(
    successes: list[bool],
    path_lengths: list[float],
    optimal_lengths: list[float],
) -> float:
    """Compute Success weighted by Path Length (SPL).

    SPL = (1/N) * sum( S_i * (L_i / max(P_i, L_i)) )
    where S_i = success, L_i = optimal path, P_i = actual path.
    """
    if not successes:
        return 0.0

    n = len(successes)
    total = 0.0
    for success, path_len, opt_len in zip(successes, path_lengths, optimal_lengths, strict=True):
        if success:
            total += opt_len / max(path_len, opt_len) if max(path_len, opt_len) > 0 else 0.0

    return total / n


def compute_success_rate(successes: list[bool]) -> float:
    """Compute success rate as fraction of successful episodes."""
    if not successes:
        return 0.0
    return sum(successes) / len(successes)


def compute_coverage(explored_cells: int, total_cells: int) -> float:
    """Compute exploration coverage ratio."""
    if total_cells == 0:
        return 0.0
    return explored_cells / total_cells
