# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.8)
project(robot_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

if(BUILD_TESTING)
  find_package(launch_testing_ament_cmake REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)
  add_launch_test(test/test_robot_launch.py)
  ament_add_pytest_test(test_navigation_params test/test_navigation_params.py)
  ament_add_pytest_test(test_hardware_launch test/test_hardware_launch.py)
endif()

ament_package()
