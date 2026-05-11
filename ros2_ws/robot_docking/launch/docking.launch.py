# SPDX-License-Identifier: Apache-2.0
"""Launch file for the docking subsystem."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("robot_docking")
    params_file = os.path.join(pkg_share, "config", "docking_params.yaml")

    return LaunchDescription(
        [
            Node(
                package="robot_docking",
                executable="apriltag_detector",
                name="apriltag_detector",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_docking",
                executable="docking_controller",
                name="docking_controller",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_docking",
                executable="visual_servo",
                name="visual_servo",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_docking",
                executable="contact_detector",
                name="contact_detector",
                parameters=[params_file],
                output="screen",
            ),
        ]
    )
