# SPDX-License-Identifier: Apache-2.0
"""Top-level launch file for robot-platform."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import xacro


def generate_launch_description():
    pkg_bringup = FindPackageShare('robot_bringup')
    pkg_description = FindPackageShare('robot_description')

    use_nav_arg = DeclareLaunchArgument(
        'use_nav', default_value='false',
        description='Launch Nav2 navigation stack')

    use_slam_arg = DeclareLaunchArgument(
        'use_slam', default_value='false',
        description='Launch SLAM toolbox for mapping')

    serial_port_arg = DeclareLaunchArgument(
        'serial_port', default_value='/dev/ttyUSB0',
        description='Serial port for micro-ROS agent')

    # Robot description
    xacro_file = PathJoinSubstitution([pkg_description, 'urdf', 'robot.urdf.xacro'])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': xacro.process_file(
            os.path.join(
                FindPackageShare('robot_description').find('robot_description'),
                'urdf', 'robot.urdf.xacro'
            )).toxml()}],
    )

    # Hardware launch
    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_bringup, 'launch', 'hardware.launch.py'])
        ),
        launch_arguments={'serial_port': LaunchConfiguration('serial_port')}.items(),
    )

    # Navigation launch (conditional)
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_bringup, 'launch', 'navigation.launch.py'])
        ),
        launch_arguments={'use_slam': LaunchConfiguration('use_slam')}.items(),
        condition=IfCondition(LaunchConfiguration('use_nav')),
    )

    return LaunchDescription([
        use_nav_arg,
        use_slam_arg,
        serial_port_arg,
        robot_state_publisher,
        hardware_launch,
        navigation_launch,
    ])
