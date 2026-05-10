// SPDX-License-Identifier: Apache-2.0
// Unit tests for external watchdog feed (TPS3813)
#include "unity.h"
#include "external_wdt.h"
#include "pin_definitions.h"

// --- Test 1: Init configures GPIO and sets low ---
void test_ext_wdt_init_sets_gpio_low(void)
{
    esp_err_t err = external_wdt_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(0, mock_get_gpio_output(EXT_WDT_FEED_GPIO));
}

// --- Test 2: EXT_WDT_FEED_GPIO is defined ---
void test_ext_wdt_gpio_defined(void)
{
    TEST_ASSERT_EQUAL(46, EXT_WDT_FEED_GPIO);
}

// --- Test 3: Feed period constant is correct ---
void test_ext_wdt_feed_period(void)
{
    TEST_ASSERT_EQUAL(500, EXT_WDT_FEED_PERIOD_MS);
}

// --- Test 4: Init returns ESP_OK ---
void test_ext_wdt_init_success(void)
{
    TEST_ASSERT_EQUAL(ESP_OK, external_wdt_init());
}
