// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "i2c_stubs.h"
#include "pin_definitions.h"

#include <string.h>

#ifndef pdTRUE
#define pdTRUE 1
#endif

#include "payload_power.h"

#define MCP_OLATA 0x14

static const power_rail_config_t test_configs[] = {
    { .name = "5V",   .mcp23017_addr = MCP23017_ADDR, .mcp23017_reg = MCP_OLATA,
      .mcp23017_bit = PAYLOAD_5V_EN_BIT,   .max_current_ma = 5000,
      .soft_start_delay_ms = 10, .overcurrent_duration_ms = 100, .enabled = true },
    { .name = "12V",  .mcp23017_addr = MCP23017_ADDR, .mcp23017_reg = MCP_OLATA,
      .mcp23017_bit = PAYLOAD_12V_EN_BIT,  .max_current_ma = 3000,
      .soft_start_delay_ms = 10, .overcurrent_duration_ms = 100, .enabled = true },
    { .name = "VBAT", .mcp23017_addr = MCP23017_ADDR, .mcp23017_reg = MCP_OLATA,
      .mcp23017_bit = PAYLOAD_VBAT_EN_BIT, .max_current_ma = 10000,
      .soft_start_delay_ms = 5, .overcurrent_duration_ms = 50, .enabled = true },
    { .name = "AUX",  .mcp23017_addr = MCP23017_ADDR, .mcp23017_reg = MCP_OLATA,
      .mcp23017_bit = 4, .max_current_ma = 2000,
      .soft_start_delay_ms = 10, .overcurrent_duration_ms = 100, .enabled = false },
};

void power_test_setUp(void)
{
    mock_i2c_reset();
    mock_set_timer(0);
}

void test_power_init_configures_rails(void)
{
    esp_err_t err = payload_power_init(test_configs, 3);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(3, payload_power_get_rail_count());
}

void test_power_init_rejects_null(void)
{
    esp_err_t err = payload_power_init(NULL, 3);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_power_init_rejects_zero_rails(void)
{
    esp_err_t err = payload_power_init(test_configs, 0);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_power_init_rejects_too_many_rails(void)
{
    esp_err_t err = payload_power_init(test_configs, POWER_RAIL_MAX + 1);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_power_enable_rail_writes_mcp_bit(void)
{
    payload_power_init(test_configs, 3);
    esp_err_t err = payload_power_enable_rail(0);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    // Verify MCP23017 was written to (write count > 0)
    int writes = mock_i2c_get_write_count(MCP23017_ADDR);
    TEST_ASSERT_TRUE(writes > 0);

    // Last write should be [OLAT_REG, value_with_bit0_set]
    size_t len = 0;
    const uint8_t *data = mock_i2c_get_last_write(MCP23017_ADDR, &len);
    TEST_ASSERT_EQUAL(2, len);
    TEST_ASSERT_EQUAL(MCP_OLATA, data[0]);
    TEST_ASSERT_TRUE(data[1] & (1 << PAYLOAD_5V_EN_BIT));
}

void test_power_disable_rail_clears_mcp_bit(void)
{
    payload_power_init(test_configs, 3);

    // Enable then disable
    payload_power_enable_rail(0);

    // Set up OLAT register mock to reflect the bit we just set
    uint8_t olat_val = (1 << PAYLOAD_5V_EN_BIT);
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    esp_err_t err = payload_power_disable_rail(0);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    size_t len = 0;
    const uint8_t *data = mock_i2c_get_last_write(MCP23017_ADDR, &len);
    TEST_ASSERT_EQUAL(2, len);
    TEST_ASSERT_EQUAL(MCP_OLATA, data[0]);
    TEST_ASSERT_FALSE(data[1] & (1 << PAYLOAD_5V_EN_BIT));
}

void test_power_disable_all_clears_all_bits(void)
{
    payload_power_init(test_configs, 3);
    payload_power_enable_rail(0);
    payload_power_enable_rail(1);
    payload_power_enable_rail(2);

    // Mock: current OLAT has bits 0,1,2 set
    uint8_t olat_val = 0x07;
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    esp_err_t err = payload_power_disable_all();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_power_state_transitions(void)
{
    mock_set_timer(0);
    payload_power_init(test_configs, 3);

    TEST_ASSERT_EQUAL(POWER_RAIL_OFF, payload_power_get_state(0));

    payload_power_enable_rail(0);
    TEST_ASSERT_EQUAL(POWER_RAIL_RAMPING, payload_power_get_state(0));

    // Simulate time beyond soft_start_delay (10ms = 10000us)
    mock_set_timer(20000);
    TEST_ASSERT_EQUAL(POWER_RAIL_ON, payload_power_get_state(0));

    // Set OLAT mock for disable read
    uint8_t olat_val = (1 << PAYLOAD_5V_EN_BIT);
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    payload_power_disable_rail(0);
    TEST_ASSERT_EQUAL(POWER_RAIL_OFF, payload_power_get_state(0));
}

void test_power_invalid_rail_index_returns_error(void)
{
    payload_power_init(test_configs, 3);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, payload_power_enable_rail(-1));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, payload_power_enable_rail(3));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, payload_power_disable_rail(99));
}

void test_power_enable_disabled_rail_returns_error(void)
{
    payload_power_init(test_configs, 4);
    // Rail index 3 (AUX) has enabled=false
    esp_err_t err = payload_power_enable_rail(3);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
}

void test_power_get_status_returns_current_state(void)
{
    payload_power_init(test_configs, 3);
    payload_power_enable_rail(1);

    power_rail_status_t status;
    esp_err_t err = payload_power_get_status(1, &status);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(POWER_RAIL_RAMPING, status.state);
}

void test_power_get_status_null_returns_error(void)
{
    payload_power_init(test_configs, 3);
    esp_err_t err = payload_power_get_status(0, NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}
