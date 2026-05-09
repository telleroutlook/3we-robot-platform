# SPDX-License-Identifier: Apache-2.0
"""Launch file for the Hailo AI perception pipeline."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the perception pipeline."""
    pkg_share = get_package_share_directory("robot_perception")
    default_params_file = os.path.join(pkg_share, "config", "inference_params.yaml")

    # Declare launch arguments
    model_path_arg = DeclareLaunchArgument(
        "model_path",
        default_value="",
        description="Path to the compiled HEF model file",
    )

    confidence_threshold_arg = DeclareLaunchArgument(
        "confidence_threshold",
        default_value="0.5",
        description="Minimum confidence score for detections",
    )

    device_id_arg = DeclareLaunchArgument(
        "device_id",
        default_value="0",
        description="Hailo device ID to use",
    )

    # Hailo inference node
    inference_node = Node(
        package="robot_perception",
        executable="inference_node",
        name="hailo_inference",
        parameters=[
            default_params_file,
            {
                "model_path": LaunchConfiguration("model_path"),
                "confidence_threshold": LaunchConfiguration("confidence_threshold"),
                "device_id": LaunchConfiguration("device_id"),
            },
        ],
        output="screen",
    )

    # Uncomment to launch a camera node alongside the perception pipeline:
    # camera_node = Node(
    #     package="v4l2_camera",
    #     executable="v4l2_camera_node",
    #     name="camera",
    #     parameters=[{
    #         "video_device": "/dev/video0",
    #         "image_size": [640, 480],
    #         "pixel_format": "YUYV",
    #     }],
    #     output="screen",
    # )

    return LaunchDescription([
        model_path_arg,
        confidence_threshold_arg,
        device_id_arg,
        inference_node,
        # camera_node,
    ])
