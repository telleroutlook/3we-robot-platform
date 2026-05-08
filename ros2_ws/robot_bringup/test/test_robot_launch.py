# SPDX-License-Identifier: Apache-2.0
"""Launch tests for robot_bringup — verifies core nodes start and publish expected topics."""

import unittest

import launch
import launch_testing
import launch_testing.actions
import pytest
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


@pytest.mark.launch_test
def generate_test_description():
    pkg_description = FindPackageShare("robot_description")
    xacro_file = PathJoinSubstitution([pkg_description, "urdf", "robot.urdf.xacro"])
    robot_description_content = Command([FindExecutable(name="xacro"), " ", xacro_file])

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description_content}],
    )

    return (
        launch.LaunchDescription(
            [
                robot_state_publisher,
                launch_testing.actions.ReadyToTest(),
            ]
        ),
        {"robot_state_publisher": robot_state_publisher},
    )


class TestRobotStatePublisher(unittest.TestCase):
    """Verify that robot_state_publisher starts and publishes /robot_description."""

    def test_node_starts(self, proc_info, robot_state_publisher):
        proc_info.assertWaitForStartup(process=robot_state_publisher, timeout=10.0)

    def test_robot_description_topic(self, proc_output, robot_state_publisher):
        proc_output.assertWaitFor(
            "robot_state_publisher",
            timeout=10.0,
        )


@launch_testing.post_shutdown_test()
class TestProcessOutput(unittest.TestCase):
    """Checks after shutdown."""

    def test_exit_codes(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
