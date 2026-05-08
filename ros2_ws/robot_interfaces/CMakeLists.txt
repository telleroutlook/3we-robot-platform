# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.8)
project(robot_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmergencyStopState.msg"
  "msg/PayloadState.msg"
  "msg/WheelSpeeds.msg"
  "srv/PayloadPower.srv"
  "srv/EmergencyStop.srv"
  DEPENDENCIES std_msgs geometry_msgs
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_interfaces test/test_interfaces.py)
endif()

ament_export_dependencies(rosidl_default_runtime)
ament_package()
