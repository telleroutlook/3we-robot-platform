# SPDX-License-Identifier: Apache-2.0
# Standalone native build for firmware unit tests (host-side, not ESP-IDF)
cmake_minimum_required(VERSION 3.16)
project(robot_firmware_tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Wno-unused-variable -Wno-unused-parameter -g")

# Unity test framework
add_library(unity STATIC
    unity/src/unity.c
)
target_include_directories(unity PUBLIC unity/src)

# ESP-IDF stubs (minimal types and mocks for host compilation)
add_library(esp_stubs STATIC
    mocks/esp_stubs.c
)
target_include_directories(esp_stubs PUBLIC mocks)

# I2C stubs for device mocking
add_library(i2c_stubs STATIC
    mocks/i2c_stubs.c
)
target_include_directories(i2c_stubs PUBLIC mocks)

# SPI stubs for MCP2515 mocking
add_library(spi_stubs STATIC
    mocks/spi_stubs.c
)
target_include_directories(spi_stubs PUBLIC mocks)

# mbedTLS stubs for crypto-dependent tests
add_library(mbedtls_stubs STATIC
    mocks/mbedtls_stubs.c
    mocks/mbedtls_ssl_stubs.c
)
target_include_directories(mbedtls_stubs PUBLIC mocks)

# LWIP socket stubs for UDP transport mocking
add_library(lwip_stubs STATIC
    mocks/lwip_stubs.c
)
target_include_directories(lwip_stubs PUBLIC mocks)

# Firmware source under test
set(FIRMWARE_SRC ${CMAKE_SOURCE_DIR}/../esp32/main)
set(FIRMWARE_CONFIG ${CMAKE_SOURCE_DIR}/../config)

# Test executable
add_executable(test_runner
    test_runner.c
    test_kinematics.c
    test_safety_clamp.c
    test_encoder_math.c
    test_battery_pct.c
    test_ota_signing.c
    test_dtls_transport.c
    test_dtls_integration.c
    test_ultrasonic_estop.c
    test_payload_hotplug.c
    test_canbus.c
    test_imu.c
    test_safety_state_machine.c
    test_thermal_monitor.c
    test_i2c_bus.c
    test_udp_transport.c
    test_display.c
    ${FIRMWARE_SRC}/motor_control.c
    ${FIRMWARE_SRC}/safety.c
    ${FIRMWARE_SRC}/encoder.c
    ${FIRMWARE_SRC}/battery.c
    ${FIRMWARE_SRC}/ota_signing.c
    ${FIRMWARE_SRC}/dtls_transport.c
    ${FIRMWARE_SRC}/payload_hotplug.c
    ${FIRMWARE_SRC}/canbus.c
    ${FIRMWARE_SRC}/imu.c
    ${FIRMWARE_SRC}/thermal_monitor.c
    ${FIRMWARE_SRC}/i2c_bus.c
    ${FIRMWARE_SRC}/udp_transport.c
    ${FIRMWARE_SRC}/display.c
)

target_include_directories(test_runner PRIVATE
    ${FIRMWARE_SRC}
    ${FIRMWARE_CONFIG}
    mocks
    unity/src
)

target_compile_definitions(test_runner PRIVATE
    UNIT_TEST_BUILD
    CONFIG_ROBOT_DISPLAY_ENABLED=1
)

# Force-include stubs so firmware sees ESP-IDF types without modification
target_compile_options(test_runner PRIVATE -include ${CMAKE_SOURCE_DIR}/mocks/esp_stubs.h)

target_link_libraries(test_runner PRIVATE unity esp_stubs i2c_stubs spi_stubs lwip_stubs mbedtls_stubs m pthread)
