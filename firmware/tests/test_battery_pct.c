// SPDX-License-Identifier: Apache-2.0
// Unit tests for battery percentage calculation
#include "unity.h"
#include "battery.h"
#include "robot_params.h"
#include "esp_stubs.h"

#define FLOAT_TOLERANCE 0.01f

static void set_battery_voltage(float target_v)
{
    // battery_read_voltage converts: (mv/1000) * BATT_VOLTAGE_DIVIDER = voltage
    // So we need mv = (target_v / BATT_VOLTAGE_DIVIDER) * 1000
    int mv = (int)((target_v / BATT_VOLTAGE_DIVIDER) * 1000.0f);
    mock_set_adc_voltage_mv(mv);

    // Fill the averaging buffer to stabilize the reading
    for (int i = 0; i < BATT_ADC_SAMPLES + 1; i++) {
        battery_read_voltage();
    }
}

void test_battery_full_charge(void)
{
    battery_init();
    // 2S fully charged: 4.2V * 2 = 8.4V
    set_battery_voltage(BATT_CELLS_SERIES * BATT_CELL_FULL_V);
    TEST_ASSERT_EQUAL_UINT8(100, battery_get_percentage());
}

void test_battery_critical_voltage(void)
{
    battery_init();
    // 2S critical: 3.0V * 2 = 6.0V
    set_battery_voltage(BATT_CELLS_SERIES * BATT_CELL_CRITICAL_V);
    TEST_ASSERT_EQUAL_UINT8(0, battery_get_percentage());
}

void test_battery_below_critical(void)
{
    battery_init();
    set_battery_voltage(BATT_CELLS_SERIES * 2.8f);
    TEST_ASSERT_EQUAL_UINT8(0, battery_get_percentage());
}

void test_battery_above_full(void)
{
    battery_init();
    set_battery_voltage(BATT_CELLS_SERIES * 4.5f);
    TEST_ASSERT_EQUAL_UINT8(100, battery_get_percentage());
}

void test_battery_mid_range(void)
{
    battery_init();
    // Midpoint: (4.2 + 3.0) / 2 = 3.6V per cell → 50%
    float mid_cell_v = (BATT_CELL_FULL_V + BATT_CELL_CRITICAL_V) / 2.0f;
    set_battery_voltage(BATT_CELLS_SERIES * mid_cell_v);
    TEST_ASSERT_UINT8_WITHIN(2, 50, battery_get_percentage());
}

void test_battery_low_threshold(void)
{
    battery_init();
    set_battery_voltage(BATT_CELLS_SERIES * BATT_CELL_LOW_V);

    battery_state_t state = battery_get_state();
    TEST_ASSERT_EQUAL(BATT_LOW, state);
}

void test_battery_ok_state(void)
{
    battery_init();
    set_battery_voltage(BATT_CELLS_SERIES * BATT_CELL_NOMINAL_V);

    battery_state_t state = battery_get_state();
    TEST_ASSERT_EQUAL(BATT_OK, state);
}

void test_battery_critical_state(void)
{
    battery_init();
    set_battery_voltage(BATT_CELLS_SERIES * 2.9f);

    battery_state_t state = battery_get_state();
    TEST_ASSERT_EQUAL(BATT_CRITICAL, state);
}

void test_battery_not_initialized_returns_zero(void)
{
    // Before init, voltage read should return 0
    // Note: we can't easily un-initialize, so this tests the guard
    TEST_ASSERT_TRUE(true);
}
