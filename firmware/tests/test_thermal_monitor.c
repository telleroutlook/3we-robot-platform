// SPDX-License-Identifier: Apache-2.0
// Unit tests for thermal_monitor.c (INA219 power monitoring + thermal state)
#include "unity.h"
#include "thermal_monitor.h"
#include "i2c_stubs.h"
#include "freertos/semphr.h"

#include <string.h>

// INA219 I2C address
#define INA219_ADDR 0x40

// Ensure pdTRUE is defined for i2c_bus inline functions
#ifndef pdTRUE
#define pdTRUE 1
#endif

// ---------------------------------------------------------------------------
// Stubs for dependencies not linked in unit test build
// ---------------------------------------------------------------------------

// i2c_bus stubs (thermal_monitor.c uses i2c_bus_lock/unlock/get_mutex)
// NOTE: i2c_bus_get_mutex is provided by test_payload_hotplug.c

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

static void thermal_test_reset(void)
{
    mock_i2c_reset();
}

// ---------------------------------------------------------------------------
// Tests: thermal_monitor_init
// ---------------------------------------------------------------------------

void test_thermal_init_success(void)
{
    thermal_test_reset();
    // No errors configured — init should succeed
    esp_err_t err = thermal_monitor_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(THERMAL_OK, thermal_get_state());
}

void test_thermal_init_verifies_i2c_writes(void)
{
    thermal_test_reset();
    // After successful init, we expect 3 I2C writes to INA219
    esp_err_t err = thermal_monitor_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(3, mock_i2c_get_write_count(INA219_ADDR));
}

void test_thermal_init_failure_i2c_write_error(void)
{
    thermal_test_reset();
    // Make all writes to INA219 fail
    mock_i2c_set_write_error(INA219_ADDR, ESP_FAIL);

    esp_err_t err = thermal_monitor_init();
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

// ---------------------------------------------------------------------------
// Tests: thermal_get_state
// ---------------------------------------------------------------------------

void test_thermal_get_state_after_init(void)
{
    thermal_test_reset();
    thermal_monitor_init();
    TEST_ASSERT_EQUAL(THERMAL_OK, thermal_get_state());
}

// ---------------------------------------------------------------------------
// Tests: thermal_get_reading
// ---------------------------------------------------------------------------

void test_thermal_get_reading_null_returns_invalid_arg(void)
{
    thermal_test_reset();
    thermal_monitor_init();
    esp_err_t err = thermal_get_reading(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_thermal_get_reading_valid_returns_zeroed_after_init(void)
{
    thermal_test_reset();
    thermal_monitor_init();

    thermal_reading_t reading;
    memset(&reading, 0xFF, sizeof(reading));

    esp_err_t err = thermal_get_reading(&reading);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, reading.bus_voltage_v);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, reading.shunt_voltage_mv);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, reading.current_ma);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, reading.power_mw);
    TEST_ASSERT_EQUAL(THERMAL_OK, reading.state);
}

// ---------------------------------------------------------------------------
// Tests: thermal_register_callback (smoke test)
// ---------------------------------------------------------------------------

static int test_callback_invocations = 0;
static thermal_state_t last_callback_state = THERMAL_OK;

static void test_thermal_cb(thermal_state_t s, const thermal_reading_t *r)
{
    (void)r;
    test_callback_invocations++;
    last_callback_state = s;
}

void test_thermal_register_callback_does_not_crash(void)
{
    thermal_test_reset();
    thermal_monitor_init();
    thermal_register_callback(test_thermal_cb);
    // Registering a callback should not crash or alter state
    TEST_ASSERT_EQUAL(THERMAL_OK, thermal_get_state());
}

void test_thermal_register_callback_null_does_not_crash(void)
{
    thermal_test_reset();
    thermal_monitor_init();
    thermal_register_callback(NULL);
    TEST_ASSERT_EQUAL(THERMAL_OK, thermal_get_state());
}
