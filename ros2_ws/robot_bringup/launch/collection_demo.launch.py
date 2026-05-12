# SPDX-License-Identifier: Apache-2.0
"""Top-level launch file for the ball collection demo.

Composes: base robot + perception + collection subsystem.
Usage:
  ros2 launch robot_bringup collection_demo.launch.py use_hailo:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    bringup_share = get_package_share_directory("robot_bringup")
    perception_share = get_package_share_directory("robot_perception")
    collection_share = get_package_share_directory("robot_collection")

    # Declare arguments
    use_hailo_arg = DeclareLaunchArgument(
        "use_hailo",
        default_value="false",
        description="Use Hailo AI inference instead of traditional CV",
    )
    map_arg = DeclareLaunchArgument(
        "map",
        default_value="",
        description="Path to Nav2 map YAML",
    )
    dump_zone_x_arg = DeclareLaunchArgument(
        "dump_zone_x",
        default_value="0.0",
        description="Dump zone X coordinate in map frame",
    )
    dump_zone_y_arg = DeclareLaunchArgument(
        "dump_zone_y",
        default_value="0.0",
        description="Dump zone Y coordinate in map frame",
    )

    # Base robot (hardware + navigation)
    robot_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "robot.launch.py")
        ),
        launch_arguments={
            "sku": "standard",
            "use_nav": "true",
            "map": LaunchConfiguration("map"),
        }.items(),
    )

    # Perception pipeline (ball detector or Hailo)
    perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(perception_share, "launch", "perception.launch.py")
        ),
        launch_arguments={
            "use_ball_detector": LaunchConfiguration("use_hailo"),
        }.items(),
    )

    # Collection subsystem
    collection_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(collection_share, "launch", "collection.launch.py")
        ),
    )

    # Camera node
    camera_node = Node(
        package="v4l2_camera",
        executable="v4l2_camera_node",
        name="camera",
        parameters=[
            {
                "video_device": "/dev/video0",
                "image_size": [640, 480],
                "pixel_format": "YUYV",
            }
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            use_hailo_arg,
            map_arg,
            dump_zone_x_arg,
            dump_zone_y_arg,
            robot_launch,
            camera_node,
            perception_launch,
            collection_launch,
        ]
    )
