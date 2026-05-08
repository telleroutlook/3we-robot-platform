// SPDX-License-Identifier: Apache-2.0
// Unit tests for CAN bus driver (MCP2515 over SPI)
#include "unity.h"
#include "canbus.h"
#include "pin_definitions.h"
#include "spi_stubs.h"
#include "esp_stubs.h"

#include <string.h>

// Helper: build a valid default config for tests
static canbus_config_t make_default_config(void)
{
    canbus_config_t cfg = {
        .spi_host = CAN_SPI_HOST,
        .pin_mosi = CAN_MOSI,
        .pin_miso = CAN_MISO,
        .pin_sclk = CAN_SCLK,
        .pin_cs = CAN_CS,
        .pin_int = CAN_INT,
        .bitrate = CAN_BITRATE_500K,
        .accept_mask = 0x7FF,
        .accept_filter = 0x000,
    };
    return cfg;
}

// ---------------------------------------------------------------------------
// Test: canbus_init with NULL config returns ESP_ERR_INVALID_ARG
// ---------------------------------------------------------------------------
void test_canbus_init_null_config(void)
{
    mock_spi_reset();
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, canbus_init(NULL));
}

// ---------------------------------------------------------------------------
// Test: canbus_init with SPI bus failure propagates error
// ---------------------------------------------------------------------------
void test_canbus_init_spi_bus_failure(void)
{
    mock_spi_reset();
    mock_spi_set_init_error(ESP_FAIL);

    canbus_config_t cfg = make_default_config();
    esp_err_t ret = canbus_init(&cfg);

    // SPI bus_initialize or bus_add_device returns ESP_FAIL
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
}

// ---------------------------------------------------------------------------
// Test: canbus_init fails when MCP2515 is not in config mode after reset
// (mock rx[2]=0x00 means CANSTAT reports MODE_NORMAL instead of MODE_CONFIG)
// ---------------------------------------------------------------------------
void test_canbus_init_not_config_mode(void)
{
    mock_spi_reset();
    // rx[2] = 0x00 → mcp2515_read_reg returns 0x00 (not config mode 0x80)
    mock_spi_set_rx_byte(2, 0x00);

    canbus_config_t cfg = make_default_config();
    esp_err_t ret = canbus_init(&cfg);

    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
}

// ---------------------------------------------------------------------------
// Test: canbus_init passes config-mode check but fails at normal-mode enter
// (mock always returns 0x80; set_mode(MODE_NORMAL) reads 0x80, expects 0x00)
// ---------------------------------------------------------------------------
void test_canbus_init_config_mode_verified(void)
{
    mock_spi_reset();
    // rx[2] = 0x80 → passes the "is config mode" check after reset
    // but mcp2515_set_mode(MODE_NORMAL) also reads 0x80, which != 0x00
    mock_spi_set_rx_byte(2, 0x80);

    canbus_config_t cfg = make_default_config();
    esp_err_t ret = canbus_init(&cfg);

    // Passes config-mode verify, but fails at "enter normal mode"
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
}

// ---------------------------------------------------------------------------
// Test: canbus_is_ready is false before successful init
// ---------------------------------------------------------------------------
void test_canbus_is_ready_initially_false(void)
{
    // Module static 'ready' starts false (or is still false after failed inits)
    TEST_ASSERT_FALSE(canbus_is_ready());
}

// ---------------------------------------------------------------------------
// Test: canbus_send with NULL frame returns ESP_ERR_INVALID_STATE
// (not ready OR frame is NULL — both check before proceeding)
// ---------------------------------------------------------------------------
void test_canbus_send_null_frame(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, canbus_send(NULL));
}

// ---------------------------------------------------------------------------
// Test: canbus_send when not ready returns ESP_ERR_INVALID_STATE
// ---------------------------------------------------------------------------
void test_canbus_send_not_ready(void)
{
    can_frame_t frame = {
        .id = 0x100,
        .extended = false,
        .rtr = false,
        .dlc = 2,
        .data = {0xAB, 0xCD},
    };
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, canbus_send(&frame));
}

// ---------------------------------------------------------------------------
// Test: canbus_set_bitrate when not ready returns ESP_ERR_INVALID_STATE
// ---------------------------------------------------------------------------
void test_canbus_set_bitrate_invalid(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, canbus_set_bitrate(CAN_BITRATE_250K));
}

// ---------------------------------------------------------------------------
// Test: canbus_set_filter when not ready returns ESP_ERR_INVALID_STATE
// ---------------------------------------------------------------------------
void test_canbus_set_filter_not_ready(void)
{
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, canbus_set_filter(0x7FF, 0x100));
}

// ---------------------------------------------------------------------------
// Test: canbus_set_recv_callback does not crash and can be set to NULL
// ---------------------------------------------------------------------------
void test_canbus_set_recv_callback(void)
{
    // Should not crash with NULL or valid pointer
    canbus_set_recv_callback(NULL);
    canbus_set_recv_callback((can_recv_callback_t)0x1234);
    canbus_set_recv_callback(NULL);
    TEST_ASSERT_TRUE(true);
}
