# SPDX-License-Identifier: Apache-2.0
# Makefile for firmware unit tests (alternative to CMake)
CC = gcc
CFLAGS = -Wall -Wextra -Wno-unused-variable -Wno-unused-parameter -g -std=c11 -DUNIT_TEST_BUILD -DCONFIG_CURRENT_SENSE_ENABLED -DCONFIG_ROBOT_DOCKING_ENABLED -DCONFIG_ROBOT_DOCKING_DIGITAL_DETECT -DCONFIG_CHARGE_DIGITAL_DETECT_GPIO=23 -DCONFIG_ROBOT_DUAL_BATTERY -DCONFIG_ENC_RR_B_ALT_GPIO=15 -DCONFIG_PI5_POWER_ENABLED -include mocks/esp_stubs.h -include mocks/mbedtls_stubs.h -include mocks/mbedtls_ssl_stubs.h

FIRMWARE_SRC = ../esp32/main
FIRMWARE_CONFIG = ../config

INCLUDES = -Imocks -Iunity/src -I$(FIRMWARE_SRC) -I$(FIRMWARE_CONFIG)

SRCS = test_runner.c \
       test_kinematics.c \
       test_safety_clamp.c \
       test_encoder_math.c \
       test_battery_pct.c \
       test_ota_signing.c \
       test_dtls_transport.c \
       test_dtls_integration.c \
       test_dtls_authority.c \
       test_ultrasonic_estop.c \
       test_payload_hotplug.c \
       test_payload_power.c \
       test_canbus.c \
       test_imu.c \
       test_safety_state_machine.c \
       test_thermal_monitor.c \
       test_i2c_bus.c \
       test_udp_transport.c \
       test_captive_portal.c \
       test_ota_update.c \
       test_ota_upload.c \
       test_ota_preflight.c \
       test_ota_compat.c \
       test_heartbeat_monitor.c \
       test_external_wdt.c \
       test_battery_multipack.c \
       test_microros_messages.c \
       test_current_sense.c \
       test_charging_detect.c \
       mocks/esp_stubs.c \
       mocks/i2c_stubs.c \
       mocks/spi_stubs.c \
       mocks/lwip_stubs.c \
       mocks/mbedtls_stubs.c \
       mocks/mbedtls_ssl_stubs.c \
       unity/src/unity.c \
       $(FIRMWARE_SRC)/motor_control.c \
       $(FIRMWARE_SRC)/safety.c \
       $(FIRMWARE_SRC)/encoder.c \
       $(FIRMWARE_SRC)/battery.c \
       $(FIRMWARE_SRC)/ota_signing.c \
       $(FIRMWARE_SRC)/ota_preflight.c \
       $(FIRMWARE_SRC)/ota_compat.c \
       $(FIRMWARE_SRC)/dtls_transport.c \
       $(FIRMWARE_SRC)/payload_hotplug.c \
       $(FIRMWARE_SRC)/payload_power.c \
       $(FIRMWARE_SRC)/canbus.c \
       $(FIRMWARE_SRC)/imu.c \
       $(FIRMWARE_SRC)/thermal_monitor.c \
       $(FIRMWARE_SRC)/i2c_bus.c \
       $(FIRMWARE_SRC)/udp_transport.c \
       $(FIRMWARE_SRC)/dtls_authority.c \
       $(FIRMWARE_SRC)/heartbeat_monitor.c \
       $(FIRMWARE_SRC)/external_wdt.c \
       $(FIRMWARE_SRC)/current_sense.c \
       $(FIRMWARE_SRC)/charging_detect.c

BUILD_DIR = build
TARGET = $(BUILD_DIR)/test_runner

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(SRCS) | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $(SRCS) -lm

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: $(TARGET)
	./$(TARGET)

clean:
	rm -rf $(BUILD_DIR)
