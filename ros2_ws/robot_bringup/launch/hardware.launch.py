# SPDX-License-Identifier: Apache-2.0
"""Hardware bringup: micro-ROS agent with QoS enforcement and static transforms."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_bringup = FindPackageShare('robot_bringup')

    serial_port_arg = DeclareLaunchArgument(
        'serial_port', default_value='/dev/ttyUSB0',
        description='Serial port for micro-ROS agent')

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate', default_value='921600',
        description='Baud rate for micro-ROS serial transport')

    qos_config_arg = DeclareLaunchArgument(
        'qos_config',
        default_value=PathJoinSubstitution([pkg_bringup, 'config', 'qos_profiles.yaml']),
        description='Path to QoS profiles configuration')

    # micro-ROS agent bridges ESP32 firmware to ROS2
    # QoS overrides ensure /cmd_vel and /emergency_stop use RELIABLE transport
    micro_ros_agent = Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        name='micro_ros_agent',
        arguments=[
            'serial',
            '--dev', LaunchConfiguration('serial_port'),
            '-b', LaunchConfiguration('baud_rate'),
        ],
        parameters=[{
            'qos_overrides./cmd_vel.publisher.reliability': 'reliable',
            'qos_overrides./cmd_vel.publisher.durability': 'volatile',
            'qos_overrides./cmd_vel.publisher.history': 'keep_last',
            'qos_overrides./cmd_vel.publisher.depth': 1,
            'qos_overrides./cmd_vel.subscription.reliability': 'reliable',
            'qos_overrides./cmd_vel.subscription.durability': 'volatile',
            'qos_overrides./cmd_vel.subscription.history': 'keep_last',
            'qos_overrides./cmd_vel.subscription.depth': 1,
            'qos_overrides./emergency_stop.publisher.reliability': 'reliable',
            'qos_overrides./emergency_stop.publisher.durability': 'transient_local',
            'qos_overrides./emergency_stop.publisher.history': 'keep_last',
            'qos_overrides./emergency_stop.publisher.depth': 10,
            'qos_overrides./emergency_stop.subscription.reliability': 'reliable',
            'qos_overrides./emergency_stop.subscription.durability': 'transient_local',
            'qos_overrides./emergency_stop.subscription.history': 'keep_last',
            'qos_overrides./emergency_stop.subscription.depth': 10,
        }],
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
        qos_config_arg,
        micro_ros_agent,
        static_tf_laser,
    ])
