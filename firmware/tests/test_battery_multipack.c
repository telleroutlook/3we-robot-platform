// SPDX-License-Identifier: Apache-2.0
// Unit tests for multi-battery pack management
#include "unity.h"
#include "battery.h"
#include "pin_definitions.h"
#include "robot_params.h"

// --- Test 1: Constants defined correctly ---
void test_battery_multipack_constants(void)
{
    TEST_ASSERT_EQUAL(2, BATT_PACKS_MAX);
    TEST_ASSERT_EQUAL(1000, BATT_PACK_PRESENT_THRESHOLD_MV);
}

// --- Test 2: Pack 2 GPIO defined ---
void test_battery_pack2_gpio_defined(void)
{
    TEST_ASSERT_EQUAL(4, BATT_PACK2_ADC_GPIO);
}

// --- Test 3: System state with single pack ---
void test_battery_system_state_single_pack(void)
{
    // After init, pack 0 is present (initialized=true)
    // Pack 1 will read 0V from mock ADC (not present)
    mock_set_adc_raw(0);
    mock_set_adc_voltage_mv(0);

    battery_system_state_t sys = battery_get_system_state();

    TEST_ASSERT_EQUAL(1, sys.num_packs_present);
    TEST_ASSERT_TRUE(sys.packs[0].present);
    TEST_ASSERT_FALSE(sys.packs[1].present);
}

// --- Test 4: Pack state struct fields ---
void test_battery_pack_state_struct(void)
{
    battery_pack_state_t pack = {
        .present = true,
        .voltage = 7.4f,
        .percentage = 50,
        .state = BATT_OK,
    };

    TEST_ASSERT_TRUE(pack.present);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 7.4f, pack.voltage);
    TEST_ASSERT_EQUAL(50, pack.percentage);
    TEST_ASSERT_EQUAL(BATT_OK, pack.state);
}

// --- Test 5: Pack 0 voltage returns non-zero after init ---
void test_battery_pack0_voltage(void)
{
    float v = battery_pack_get_voltage(0);
    // After battery_init() in earlier tests, voltage_avg is set to some value
    // Just verify it returns a value (the exact value depends on mock ADC state)
    TEST_ASSERT_TRUE(v > 0.0f);
}

// --- Test 6: Invalid pack index ---
void test_battery_invalid_pack_index(void)
{
    TEST_ASSERT_FALSE(battery_pack_is_present(2));
    TEST_ASSERT_FALSE(battery_pack_is_present(255));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, battery_pack_get_voltage(2));
}

// --- Test 7: System state reports at least one pack ---
void test_battery_system_state_worst_state(void)
{
    battery_system_state_t sys = battery_get_system_state();
    // Pack 0 is always present (initialized=true)
    TEST_ASSERT_TRUE(sys.num_packs_present >= 1);
    // worst_state is a valid enum value
    TEST_ASSERT_TRUE(sys.worst_state <= BATT_CRITICAL);
}
