# SPDX-License-Identifier: Apache-2.0
"""Gymnasium-compatible environments for RL training on the 3we platform.

Register environments so they can be created with:
    env = gymnasium.make("3we/Navigation-v1")
    env = gymnasium.make("3we/Exploration-v1")
"""

from __future__ import annotations

from threewe.gym.envs import ExplorationEnv, NavigationEnv

__all__ = ["NavigationEnv", "ExplorationEnv"]

try:
    import gymnasium

    gymnasium.register(
        id="3we/Navigation-v1",
        entry_point="threewe.gym.envs:NavigationEnv",
    )
    gymnasium.register(
        id="3we/Exploration-v1",
        entry_point="threewe.gym.envs:ExplorationEnv",
    )
except ImportError:
    pass
