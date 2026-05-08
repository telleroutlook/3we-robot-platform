# SPDX-License-Identifier: Apache-2.0
# Makefile for firmware unit tests (alternative to CMake)
CC = gcc
CFLAGS = -Wall -Wextra -Wno-unused-variable -Wno-unused-parameter -g -std=c11 -DUNIT_TEST_BUILD -include mocks/esp_stubs.h -include mocks/mbedtls_stubs.h -include mocks/mbedtls_ssl_stubs.h

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
       mocks/esp_stubs.c \
       mocks/mbedtls_stubs.c \
       mocks/mbedtls_ssl_stubs.c \
       unity/src/unity.c \
       $(FIRMWARE_SRC)/motor_control.c \
       $(FIRMWARE_SRC)/safety.c \
       $(FIRMWARE_SRC)/encoder.c \
       $(FIRMWARE_SRC)/battery.c \
       $(FIRMWARE_SRC)/ota_signing.c \
       $(FIRMWARE_SRC)/dtls_transport.c

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
