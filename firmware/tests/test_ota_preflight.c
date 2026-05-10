// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "ota_preflight.h"

#include <string.h>
#include <stdint.h>
#include <stdbool.h>

// The preflight module calls battery_get_percentage(), safety_get_state(),
// motor_is_stopped(), thermal_get_state(), and esp_wifi_sta_get_ap_info().
// For host-side tests, we test the preflight logic by directly exercising
// the NVS-based boot failure counter (which is pure logic testable via mocks)
// and verifying the struct layout and thresholds as compile-time checks.

void test_preflight_result_struct_has_expected_fields(void)
{
    ota_preflight_result_t r = {0};
    r.battery_ok = true;
    r.wifi_ok = true;
    r.safety_ok = true;
    r.motors_idle = true;
    r.thermal_ok = true;
    r.overall_pass = true;
    r.battery_pct = 80;
    r.wifi_rssi = -50;
    r.fail_reason[0] = '\0';
    TEST_ASSERT_TRUE(r.overall_pass);
    TEST_ASSERT_EQUAL(80, r.battery_pct);
    TEST_ASSERT_EQUAL(-50, r.wifi_rssi);
}

void test_preflight_thresholds_correct(void)
{
    TEST_ASSERT_EQUAL(50, OTA_PREFLIGHT_MIN_BATTERY_PCT);
    TEST_ASSERT_EQUAL(-70, OTA_PREFLIGHT_MIN_WIFI_RSSI);
    TEST_ASSERT_EQUAL(30000, OTA_PREFLIGHT_VALIDATION_TIMEOUT_MS);
    TEST_ASSERT_EQUAL(3, OTA_PREFLIGHT_MAX_BOOT_FAILURES);
}

void test_preflight_boot_fail_count_initial_zero(void)
{
    ota_preflight_clear_boot_fail();
    TEST_ASSERT_EQUAL(0, ota_preflight_get_boot_fail_count());
}

void test_preflight_boot_fail_increment(void)
{
    ota_preflight_clear_boot_fail();
    ota_preflight_increment_boot_fail();
    TEST_ASSERT_EQUAL(1, ota_preflight_get_boot_fail_count());
    ota_preflight_increment_boot_fail();
    TEST_ASSERT_EQUAL(2, ota_preflight_get_boot_fail_count());
}

void test_preflight_boot_fail_clear(void)
{
    ota_preflight_clear_boot_fail();
    ota_preflight_increment_boot_fail();
    ota_preflight_increment_boot_fail();
    ota_preflight_increment_boot_fail();
    ota_preflight_clear_boot_fail();
    TEST_ASSERT_EQUAL(0, ota_preflight_get_boot_fail_count());
}

void test_preflight_boot_fail_reaches_max(void)
{
    ota_preflight_clear_boot_fail();
    for (int i = 0; i < OTA_PREFLIGHT_MAX_BOOT_FAILURES; i++) {
        ota_preflight_increment_boot_fail();
    }
    uint8_t count = ota_preflight_get_boot_fail_count();
    TEST_ASSERT_EQUAL(OTA_PREFLIGHT_MAX_BOOT_FAILURES, count);
    TEST_ASSERT_TRUE(count >= OTA_PREFLIGHT_MAX_BOOT_FAILURES);
}

void test_preflight_fail_reason_buffer_size(void)
{
    ota_preflight_result_t r = {0};
    TEST_ASSERT_EQUAL(64, sizeof(r.fail_reason));
}
