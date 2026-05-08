# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    "../config"
    "managed_components"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(robot_platform_firmware)
