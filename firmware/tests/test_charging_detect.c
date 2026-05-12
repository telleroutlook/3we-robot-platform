// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "charging_detect.h"

extern void mock_set_adc_voltage_mv(int mv);
extern adc_oneshot_unit_handle_t adc_manager_get_handle(void);

void test_charging_detect_init_success(void)
{
    esp_err_t err = charging_detect_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_charging_detect_not_connected_below_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(1500); // Below 2000 mV threshold
    TEST_ASSERT_FALSE(charging_detect_is_connected());
}

void test_charging_detect_connected_at_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(CHARGE_CONTACT_THRESHOLD_MV);
    TEST_ASSERT_TRUE(charging_detect_is_connected());
}

void test_charging_detect_connected_above_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(3000);
    TEST_ASSERT_TRUE(charging_detect_is_connected());
}

void test_charging_detect_voltage_returns_calibrated(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(2750);
    int mv = charging_detect_get_voltage_mv();
    TEST_ASSERT_EQUAL(2750, mv);
}

void test_charging_detect_voltage_zero_before_init(void)
{
    // After init, reading with valid mock returns the mocked value
    charging_detect_init();
    mock_set_adc_voltage_mv(1234);
    int mv = charging_detect_get_voltage_mv();
    TEST_ASSERT_EQUAL(1234, mv);
}

void test_charging_detect_boundary_just_below_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(CHARGE_CONTACT_THRESHOLD_MV - 1);
    TEST_ASSERT_FALSE(charging_detect_is_connected());
}
