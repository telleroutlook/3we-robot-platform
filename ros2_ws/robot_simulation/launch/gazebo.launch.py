# SPDX-License-Identifier: Apache-2.0
"""Launch Gazebo Fortress with the robot platform model, ros_gz_bridge, and RViz2."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_simulation = FindPackageShare("robot_simulation")
    pkg_ros_gz_sim = FindPackageShare("ros_gz_sim")

    # --- Arguments ---
    world_arg = DeclareLaunchArgument(
        "world",
        default_value=PathJoinSubstitution([pkg_simulation, "worlds", "empty.sdf"]),
        description="Path to the Gazebo world SDF file",
    )

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Launch RViz2 alongside the simulation",
    )

    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=PathJoinSubstitution(
            [pkg_simulation, "rviz", "sim_default.rviz"]
        ),
        description="Path to RViz2 configuration file",
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation (Gazebo) clock",
    )

    # --- Robot description ---
    robot_description_content = Command(
        [
            FindExecutable(name="xacro"),
            " ",
            PathJoinSubstitution([pkg_simulation, "urdf", "robot_gazebo.urdf.xacro"]),
        ]
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {
                "robot_description": robot_description_content,
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }
        ],
        output="screen",
    )

    # --- Gazebo Fortress ---
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_ros_gz_sim, "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={
            "gz_args": ["-r ", LaunchConfiguration("world")],
            "on_exit_shutdown": "true",
        }.items(),
    )

    # Spawn the robot into the Gazebo world
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
            "0.1",
        ],
        output="screen",
    )

    # --- ros_gz_bridge ---
    bridge_params_file = PathJoinSubstitution(
        [pkg_simulation, "config", "bridge_params.yaml"]
    )

    ros_gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": bridge_params_file,
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }
        ],
        output="screen",
    )

    # --- RViz2 ---
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        parameters=[
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }
        ],
        condition=IfCondition(LaunchConfiguration("use_rviz")),
        output="screen",
    )

    return LaunchDescription(
        [
            # Arguments
            world_arg,
            use_rviz_arg,
            rviz_config_arg,
            use_sim_time_arg,
            # Nodes and processes
            robot_state_publisher_node,
            # joint_state_publisher removed: Gazebo bridge provides /joint_states
            gazebo,
            spawn_robot,
            ros_gz_bridge_node,
            rviz_node,
        ]
    )
