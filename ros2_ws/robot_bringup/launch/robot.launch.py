# SPDX-License-Identifier: Apache-2.0
"""Top-level launch file for robot-platform."""

from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

INDUSTRIAL_XACRO_ARGS = (
    " chassis_length:=0.500 chassis_width:=0.400 chassis_height:=0.100"
    " chassis_mass:=3.5 wheel_radius:=0.0485 wheel_width:=0.060"
    " wheel_mass:=0.35 wheelbase:=0.300 track_width:=0.320"
)


def _launch_setup(context: LaunchContext):
    import subprocess

    sku = context.launch_configurations["sku"]
    use_sim_time = context.launch_configurations["use_sim_time"]
    serial_port = context.launch_configurations["serial_port"]

    pkg_bringup = FindPackageShare("robot_bringup")

    xacro_path_str = (
        subprocess.check_output(
            ["ros2", "pkg", "prefix", "robot_description"], text=True
        ).strip()
        + "/share/robot_description/urdf/robot.urdf.xacro"
    )

    xacro_args = ["xacro", xacro_path_str]
    if sku == "industrial":
        xacro_args += INDUSTRIAL_XACRO_ARGS.split()

    robot_description_content = subprocess.check_output(xacro_args, text=True)

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {
                "robot_description": robot_description_content,
                "use_sim_time": use_sim_time == "true",
            }
        ],
    )

    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_bringup, "launch", "hardware.launch.py"])
        ),
        launch_arguments={"serial_port": serial_port}.items(),
    )

    nav_params_file = (
        "nav2_params_industrial.yaml" if sku == "industrial" else "nav2_params.yaml"
    )
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_bringup, "launch", "navigation.launch.py"])
        ),
        launch_arguments={
            "use_slam": context.launch_configurations["use_slam"],
            "use_sim_time": use_sim_time,
            "map": context.launch_configurations["map"],
            "params_file": PathJoinSubstitution(
                [pkg_bringup, "config", nav_params_file]
            ),
        }.items(),
        condition=IfCondition(LaunchConfiguration("use_nav")),
    )

    return [robot_state_publisher, hardware_launch, navigation_launch]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "sku",
                default_value="standard",
                description="Robot SKU variant (basic|standard|pro|industrial)",
            ),
            DeclareLaunchArgument(
                "use_nav",
                default_value="false",
                description="Launch Nav2 navigation stack",
            ),
            DeclareLaunchArgument(
                "use_slam",
                default_value="false",
                description="Launch SLAM toolbox for mapping",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock",
            ),
            DeclareLaunchArgument(
                "map",
                default_value="",
                description="Path to map YAML file (required when use_slam=false)",
            ),
            DeclareLaunchArgument(
                "serial_port",
                default_value="/dev/ttyUSB0",
                description="Serial port for micro-ROS agent",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
