# SPDX-License-Identifier: Apache-2.0
"""Navigation stack launch: Nav2 + optional SLAM."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_bringup = FindPackageShare("robot_bringup")

    default_nav2_params = PathJoinSubstitution(
        [pkg_bringup, "config", "nav2_params.yaml"]
    )
    slam_params_file = PathJoinSubstitution([pkg_bringup, "config", "slam_params.yaml"])

    use_slam_arg = DeclareLaunchArgument(
        "use_slam",
        default_value="false",
        description="Run SLAM toolbox for mapping mode",
    )

    map_file_arg = DeclareLaunchArgument(
        "map",
        default_value="",
        description="Path to map YAML file (required if use_slam=false)",
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false", description="Use simulation clock"
    )

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=default_nav2_params,
        description="Path to Nav2 parameters file",
    )

    # Nav2 bringup
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("nav2_bringup"), "launch", "navigation_launch.py"]
            )
        ),
        launch_arguments={
            "params_file": LaunchConfiguration("params_file"),
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "map": LaunchConfiguration("map"),
        }.items(),
    )

    # SLAM toolbox (mapping mode)
    slam_node = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        parameters=[
            slam_params_file,
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
        condition=IfCondition(LaunchConfiguration("use_slam")),
        output="screen",
    )

    return LaunchDescription(
        [
            use_slam_arg,
            map_file_arg,
            use_sim_time_arg,
            params_file_arg,
            nav2_launch,
            slam_node,
        ]
    )
