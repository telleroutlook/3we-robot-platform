# SPDX-License-Identifier: Apache-2.0
"""Gymnasium-compatible environments for RL training on the 3we platform.

Register environments so they can be created with:
    env = gymnasium.make("3we/Navigation-v1")
    env = gymnasium.make("3we/Exploration-v1")
    env = gymnasium.make("3we/ObjectNav-v1")
    env = gymnasium.make("3we/VLN-v1")
    env = gymnasium.make("3we/MultiAgent-v1")
"""

from __future__ import annotations

from threewe.gym.envs import ActionLevel, ExplorationEnv, NavigationEnv, ObjectNavEnv, VLNEnv
from threewe.gym.multiagent import MultiAgentEnv

__all__ = [
    "ActionLevel",
    "NavigationEnv",
    "ExplorationEnv",
    "ObjectNavEnv",
    "VLNEnv",
    "MultiAgentEnv",
]

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
    gymnasium.register(
        id="3we/ObjectNav-v1",
        entry_point="threewe.gym.envs:ObjectNavEnv",
    )
    gymnasium.register(
        id="3we/VLN-v1",
        entry_point="threewe.gym.envs:VLNEnv",
    )
except ImportError:
    pass
