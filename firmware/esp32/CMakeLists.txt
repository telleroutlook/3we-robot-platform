# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    "../config"
)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/managed_components")
    list(APPEND EXTRA_COMPONENT_DIRS "managed_components")
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(robot_platform_firmware)
