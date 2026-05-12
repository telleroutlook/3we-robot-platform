// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "charging_detect.h"
#include "pin_definitions.h"

extern void mock_set_adc_voltage_mv(int mv);
extern void mock_set_gpio_level(int gpio, int level);
extern adc_oneshot_unit_handle_t adc_manager_get_handle(void);

void test_charging_detect_init_success(void)
{
    esp_err_t err = charging_detect_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_charging_detect_not_connected_below_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(1500);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 1); // not asserted
#endif
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
    charging_detect_init();
    mock_set_adc_voltage_mv(1234);
    int mv = charging_detect_get_voltage_mv();
    TEST_ASSERT_EQUAL(1234, mv);
}

void test_charging_detect_boundary_just_below_threshold(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(CHARGE_CONTACT_THRESHOLD_MV - 1);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 1); // not asserted
#endif
    TEST_ASSERT_FALSE(charging_detect_is_connected());
}

#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
void test_charging_detect_digital_asserted_when_low(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(0);
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 0);
    TEST_ASSERT_TRUE(charging_detect_is_connected());
}

void test_charging_detect_connected_via_analog_only(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(2500);
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 1); // digital NOT asserted
    TEST_ASSERT_TRUE(charging_detect_is_connected());
    TEST_ASSERT_EQUAL(CHARGE_DETECT_ANALOG, charging_detect_get_method());
}

void test_charging_detect_connected_via_digital_only(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(500); // below analog threshold
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 0); // digital asserted
    TEST_ASSERT_TRUE(charging_detect_is_connected());
    TEST_ASSERT_EQUAL(CHARGE_DETECT_DIGITAL, charging_detect_get_method());
}

void test_charging_detect_method_reports_both(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(2500); // above analog threshold
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 0); // digital asserted
    TEST_ASSERT_TRUE(charging_detect_is_connected());
    TEST_ASSERT_EQUAL(CHARGE_DETECT_BOTH, charging_detect_get_method());
}
#endif

void test_charging_detect_method_analog_when_connected(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(2500);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 1);
#endif
    TEST_ASSERT_EQUAL(CHARGE_DETECT_ANALOG, charging_detect_get_method());
}

void test_charging_detect_method_none_when_disconnected(void)
{
    charging_detect_init();
    mock_set_adc_voltage_mv(500);
#ifdef CONFIG_ROBOT_DOCKING_DIGITAL_DETECT
    mock_set_gpio_level(CHARGE_DIGITAL_DETECT_GPIO, 1);
#endif
    TEST_ASSERT_EQUAL(CHARGE_DETECT_NONE, charging_detect_get_method());
}
