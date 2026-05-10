# SPDX-License-Identifier: Apache-2.0
"""Launch Gazebo Fortress with the robot platform model, ros_gz_bridge, and RViz2."""

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
    pkg_simulation = FindPackageShare("robot_simulation")
    pkg_ros_gz_sim = FindPackageShare("ros_gz_sim")

    sim_pkg_path = subprocess.check_output(
        ["ros2", "pkg", "prefix", "robot_simulation"], text=True
    ).strip()
    xacro_path = f"{sim_pkg_path}/share/robot_simulation/urdf/robot_gazebo.urdf.xacro"

    xacro_cmd = f"xacro {xacro_path}"
    if sku == "industrial":
        xacro_cmd += INDUSTRIAL_XACRO_ARGS

    robot_description_content = subprocess.check_output(
        xacro_cmd, shell=True, text=True
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {
                "robot_description": robot_description_content,
                "use_sim_time": context.launch_configurations["use_sim_time"] == "true",
            }
        ],
        output="screen",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ros_gz_sim, "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={
            "gz_args": f"-r {context.launch_configurations['world']}",
            "on_exit_shutdown": "true",
        }.items(),
    )

    spawn_z = "0.15" if sku == "industrial" else "0.1"
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "robot_platform",
            "-topic",
            "robot_description",
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            spawn_z,
        ],
        output="screen",
    )

    bridge_params_file = PathJoinSubstitution(
        [pkg_simulation, "config", "bridge_params.yaml"]
    )

    ros_gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": bridge_params_file,
                "use_sim_time": context.launch_configurations["use_sim_time"] == "true",
            }
        ],
        output="screen",
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", context.launch_configurations["rviz_config"]],
        parameters=[
            {
                "use_sim_time": context.launch_configurations["use_sim_time"] == "true",
            }
        ],
        condition=IfCondition(LaunchConfiguration("use_rviz")),
        output="screen",
    )

    return [
        robot_state_publisher_node,
        gazebo,
        spawn_robot,
        ros_gz_bridge_node,
        rviz_node,
    ]


def generate_launch_description():
    pkg_simulation = FindPackageShare("robot_simulation")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "sku",
                default_value="standard",
                description="Robot SKU variant (basic|standard|pro|industrial)",
            ),
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [pkg_simulation, "worlds", "empty.sdf"]
                ),
                description="Path to the Gazebo world SDF file",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Launch RViz2 alongside the simulation",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=PathJoinSubstitution(
                    [pkg_simulation, "rviz", "sim_default.rviz"]
                ),
                description="Path to RViz2 configuration file",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use simulation (Gazebo) clock",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
