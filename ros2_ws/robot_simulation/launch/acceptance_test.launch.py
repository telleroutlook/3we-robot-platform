# SPDX-License-Identifier: Apache-2.0
"""
Simulation acceptance test launch file.

Launches headless Gazebo with Nav2 for automated patrol testing.
Extends gazebo_nav.launch.py with acceptance-specific configuration.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_simulation = FindPackageShare("robot_simulation")

    headless_arg = DeclareLaunchArgument(
        "headless", default_value="true", description="Run Gazebo without GUI (for CI)"
    )

    trials_arg = DeclareLaunchArgument(
        "trials", default_value="10", description="Number of patrol trials to run"
    )

    timeout_arg = DeclareLaunchArgument(
        "timeout_per_trial",
        default_value="120",
        description="Timeout per trial in seconds",
    )

    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_simulation, "launch", "gazebo_nav.launch.py"])
        ),
        launch_arguments={
            "world": PathJoinSubstitution([pkg_simulation, "worlds", "obstacles.sdf"]),
            "headless": LaunchConfiguration("headless"),
            "sku": "standard",
            "use_rviz": "false",
        }.items(),
    )

    return LaunchDescription(
        [
            headless_arg,
            trials_arg,
            timeout_arg,
            nav_launch,
        ]
    )
