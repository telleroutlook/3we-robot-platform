# SPDX-License-Identifier: Apache-2.0
"""Launch Gazebo Fortress simulation with full Nav2 navigation stack."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_simulation = FindPackageShare("robot_simulation")
    pkg_bringup = FindPackageShare("robot_bringup")
    pkg_nav2_bringup = FindPackageShare("nav2_bringup")

    # --- Arguments ---
    world_arg = DeclareLaunchArgument(
        "world",
        default_value=PathJoinSubstitution([pkg_simulation, "worlds", "obstacles.sdf"]),
        description="Path to the Gazebo world SDF file",
    )

    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description="Run Gazebo in server-only mode (no GUI)",
    )

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Launch RViz2 with Nav2 configuration",
    )

    sku_arg = DeclareLaunchArgument(
        "sku",
        default_value="standard",
        description="Robot SKU variant",
    )

    map_arg = DeclareLaunchArgument(
        "map",
        default_value="",
        description="Path to map YAML file for localization mode",
    )

    use_slam_arg = DeclareLaunchArgument(
        "use_slam",
        default_value="true",
        description="Run SLAM toolbox instead of AMCL localization",
    )

    nav2_params_arg = DeclareLaunchArgument(
        "nav2_params",
        default_value=PathJoinSubstitution(
            [pkg_simulation, "config", "nav2_params_sim.yaml"]
        ),
        description="Path to Nav2 parameters file (defaults to simulation overlay)",
    )

    # --- Include base Gazebo simulation ---
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_simulation, "launch", "gazebo.launch.py"])
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "headless": LaunchConfiguration("headless"),
            "sku": LaunchConfiguration("sku"),
            "use_sim_time": "true",
            "use_rviz": "false",
        }.items(),
    )

    # --- Include Nav2 + SLAM from robot_bringup (single unified stack) ---
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_bringup, "launch", "navigation.launch.py"])
        ),
        launch_arguments={
            "use_slam": LaunchConfiguration("use_slam"),
            "map": LaunchConfiguration("map"),
            "use_sim_time": "true",
            "params_file": LaunchConfiguration("nav2_params"),
        }.items(),
    )

    # --- RViz with Nav2 config (disabled in headless mode) ---
    rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_nav2_bringup, "launch", "rviz_launch.py"])
        ),
        launch_arguments={
            "use_sim_time": "true",
        }.items(),
        condition=IfCondition(LaunchConfiguration("use_rviz")),
    )

    return LaunchDescription(
        [
            # Arguments
            world_arg,
            headless_arg,
            use_rviz_arg,
            sku_arg,
            map_arg,
            use_slam_arg,
            nav2_params_arg,
            # Launch includes
            gazebo_launch,
            navigation_launch,
            rviz_launch,
        ]
    )
