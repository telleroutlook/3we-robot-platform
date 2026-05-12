// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "current_sense.h"
#include <string.h>

// Access mock helpers from esp_stubs
extern void mock_set_adc_voltage_mv(int mv);
extern void mock_set_timer(int64_t value);
extern adc_oneshot_unit_handle_t adc_manager_get_handle(void);

// Helper: Convert current in mA to expected ADC voltage in mV.
// ACS712-05B: sensitivity = 185 mV/A, zero-current output = 2500 mV
// voltage_mv = 2500 + (current_mA / 1000) * 185
static int current_to_voltage_mv(float current_ma)
{
    return (int)(2500.0f + (current_ma / 1000.0f) * 185.0f);
}

static void reset_current_sense(void)
{
    // Re-init to clear state
    current_sense_init();
}

// --- Tests ---

void test_current_sense_init_returns_ok(void)
{
    esp_err_t err = current_sense_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_current_sense_read_null_returns_invalid_arg(void)
{
    current_sense_init();
    esp_err_t err = current_sense_read(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_current_sense_read_zeroed_after_init(void)
{
    current_sense_init();
    current_reading_t reading;
    esp_err_t err = current_sense_read(&reading);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, reading.total_current_ma);
    TEST_ASSERT_EQUAL(0, reading.overcurrent_flags);
}

void test_current_sense_get_state_invalid_channel(void)
{
    current_sense_init();
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(-1));
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(CURRENT_SENSE_CHANNELS));
}

void test_current_sense_get_state_normal_after_init(void)
{
    current_sense_init();
    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(i));
    }
}

void test_current_sense_update_zero_current(void)
{
    reset_current_sense();
    // 2500 mV = 0A for ACS712
    mock_set_adc_voltage_mv(2500);
    mock_set_timer(1000000); // 1 second

    current_sense_update();

    current_reading_t reading;
    current_sense_read(&reading);
    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        TEST_ASSERT_FLOAT_WITHIN(1.0f, 0.0f, reading.current_ma[i]);
    }
    TEST_ASSERT_FLOAT_WITHIN(4.0f, 0.0f, reading.total_current_ma);
    TEST_ASSERT_EQUAL(0, reading.overcurrent_flags);
}

void test_current_sense_update_normal_current(void)
{
    reset_current_sense();
    // 1000 mA = 2500 + (1000/1000)*185 = 2685 mV
    mock_set_adc_voltage_mv(current_to_voltage_mv(1000.0f));
    mock_set_timer(2000000);

    current_sense_update();

    current_reading_t reading;
    current_sense_read(&reading);
    for (int i = 0; i < CURRENT_SENSE_CHANNELS; i++) {
        TEST_ASSERT_FLOAT_WITHIN(50.0f, 1000.0f, reading.current_ma[i]);
    }
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(0));
}

void test_current_sense_soft_limit_requires_duration(void)
{
    reset_current_sense();
    // 3500 mA: above soft (3000) but below hard (8000)
    mock_set_adc_voltage_mv(current_to_voltage_mv(3500.0f));

    // First update at t=1ms: starts counting
    mock_set_timer(1000);
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(0));

    // Still below 100ms threshold
    mock_set_timer(51 * 1000); // 51ms
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(0));

    // At 101ms: should trigger soft limit (100ms elapsed since start at 1ms)
    mock_set_timer(101 * 1000); // 101ms
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_SOFT_LIMIT, current_sense_get_state(0));
}

void test_current_sense_hard_limit_triggers_after_duration(void)
{
    reset_current_sense();
    // 9000 mA: above hard limit (8000)
    mock_set_adc_voltage_mv(current_to_voltage_mv(9000.0f));

    // First update at t=1ms
    mock_set_timer(1000);
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(0));

    // At 21ms: should trigger hard limit (20ms elapsed since 1ms)
    mock_set_timer(21 * 1000); // 21ms
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_HARD_LIMIT, current_sense_get_state(0));
}

void test_current_sense_overcurrent_clears_when_normal(void)
{
    reset_current_sense();
    // Trigger soft limit first
    mock_set_adc_voltage_mv(current_to_voltage_mv(3500.0f));
    mock_set_timer(1000);
    current_sense_update();
    mock_set_timer(101 * 1000);
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_SOFT_LIMIT, current_sense_get_state(0));

    // Return to normal current
    mock_set_adc_voltage_mv(current_to_voltage_mv(500.0f));
    mock_set_timer(200 * 1000);
    current_sense_update();
    TEST_ASSERT_EQUAL(CURRENT_OK, current_sense_get_state(0));
}

void test_current_sense_total_current_sums_channels(void)
{
    reset_current_sense();
    // Mock returns same value for all channels
    mock_set_adc_voltage_mv(current_to_voltage_mv(1000.0f));
    mock_set_timer(1000000);
    current_sense_update();

    current_reading_t reading;
    current_sense_read(&reading);
    // 4 channels * ~1000 mA each
    TEST_ASSERT_FLOAT_WITHIN(200.0f, 4000.0f, reading.total_current_ma);
}

void test_current_sense_hard_limit_sets_overcurrent_flags(void)
{
    reset_current_sense();
    mock_set_adc_voltage_mv(current_to_voltage_mv(9000.0f));
    mock_set_timer(1000);
    current_sense_update();
    mock_set_timer(21 * 1000);
    current_sense_update();

    current_reading_t reading;
    current_sense_read(&reading);
    // All channels get same mock value, so all should be flagged
    TEST_ASSERT_TRUE(reading.overcurrent_flags != 0);
}

void test_current_sense_negative_current_uses_absolute(void)
{
    reset_current_sense();
    // Below zero-point: simulates negative current (reverse direction)
    // 2500 - 185 = 2315 mV would be -1000 mA, but abs gives 1000 mA
    mock_set_adc_voltage_mv(2315);
    mock_set_timer(1000000);
    current_sense_update();

    current_reading_t reading;
    current_sense_read(&reading);
    TEST_ASSERT_FLOAT_WITHIN(100.0f, 1000.0f, reading.current_ma[0]);
}
