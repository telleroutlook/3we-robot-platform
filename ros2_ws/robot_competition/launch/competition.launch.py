# SPDX-License-Identifier: Apache-2.0
"""Launch all competition nodes for RoboCup Logistics League."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    team_name_arg = DeclareLaunchArgument(
        "team_name", default_value="3WE", description="RCLL team name"
    )
    referee_host_arg = DeclareLaunchArgument(
        "referee_host", default_value="192.168.1.1", description="Referee box IP"
    )

    referee_client = Node(
        package="robot_competition",
        executable="referee_client",
        name="referee_client",
        parameters=[
            {
                "referee_host": LaunchConfiguration("referee_host"),
                "team_name": LaunchConfiguration("team_name"),
            }
        ],
    )

    mps_detector = Node(
        package="robot_competition",
        executable="mps_detector",
        name="mps_detector",
    )

    task_executor = Node(
        package="robot_competition",
        executable="task_executor",
        name="task_executor",
    )

    fleet_coordinator = Node(
        package="robot_competition",
        executable="fleet_coordinator",
        name="fleet_coordinator",
        parameters=[{"robot_count": 3}],
    )

    return LaunchDescription(
        [
            team_name_arg,
            referee_host_arg,
            referee_client,
            mps_detector,
            task_executor,
            fleet_coordinator,
        ]
    )
