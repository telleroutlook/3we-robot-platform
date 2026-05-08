# SPDX-License-Identifier: Apache-2.0
"""Hardware bringup: micro-ROS agent and static transforms."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    serial_port_arg = DeclareLaunchArgument(
        'serial_port', default_value='/dev/ttyUSB0',
        description='Serial port for micro-ROS agent')

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate', default_value='921600',
        description='Baud rate for micro-ROS serial transport')

    # micro-ROS agent bridges ESP32 firmware to ROS2
    micro_ros_agent = Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        name='micro_ros_agent',
        arguments=[
            'serial',
            '--dev', LaunchConfiguration('serial_port'),
            '-b', LaunchConfiguration('baud_rate'),
        ],
        output='screen',
    )

    # Static transform: base_link -> laser (if LiDAR attached)
    static_tf_laser = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='laser_tf',
        arguments=['0', '0', '0.12', '0', '0', '0', 'base_link', 'laser_frame'],
    )

    return LaunchDescription([
        serial_port_arg,
        baud_rate_arg,
        micro_ros_agent,
        static_tf_laser,
    ])
