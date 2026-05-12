# SPDX-License-Identifier: Apache-2.0
"""Launch file for the ball collection subsystem."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("robot_collection")
    params_file = os.path.join(pkg_share, "config", "collection_params.yaml")

    return LaunchDescription(
        [
            Node(
                package="robot_collection",
                executable="ball_tracker",
                name="ball_tracker",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_collection",
                executable="arm_controller",
                name="arm_controller",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_collection",
                executable="basket_controller",
                name="basket_controller",
                parameters=[params_file],
                output="screen",
            ),
            Node(
                package="robot_collection",
                executable="collection_manager",
                name="collection_manager",
                parameters=[params_file],
                output="screen",
            ),
        ]
    )
