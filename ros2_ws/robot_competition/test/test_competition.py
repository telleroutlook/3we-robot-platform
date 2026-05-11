# SPDX-License-Identifier: Apache-2.0
"""Basic tests for robot_competition package."""


def test_package_import():
    import robot_competition  # noqa: F401


def test_referee_client_import():
    from robot_competition.referee_client_node import RefereeClientNode  # noqa: F401


def test_mps_detector_import():
    from robot_competition.mps_detector_node import MpsDetectorNode  # noqa: F401


def test_task_executor_import():
    from robot_competition.task_executor_node import TaskExecutorNode  # noqa: F401


def test_fleet_coordinator_import():
    from robot_competition.fleet_coordinator_node import FleetCoordinatorNode  # noqa: F401
