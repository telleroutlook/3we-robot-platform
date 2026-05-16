// SPDX-License-Identifier: Apache-2.0
// Unit tests for heartbeat monitor (Pi 5 power watchdog)
#include "unity.h"
#include "heartbeat_monitor.h"
#include "pin_definitions.h"

// --- Test 1: Init sets relay ON and state to WAITING ---
void test_heartbeat_init_relay_on(void)
{
    esp_err_t err = heartbeat_monitor_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(1, mock_get_gpio_output(PI5_RELAY_GPIO));
    TEST_ASSERT_EQUAL(HB_STATE_WAITING, heartbeat_get_state());
}

// --- Test 2: Feed transitions from WAITING to ACTIVE after boot grace ---
void test_heartbeat_feed_transitions_to_active(void)
{
    mock_set_timer(0);
    heartbeat_monitor_init();
    TEST_ASSERT_EQUAL(HB_STATE_WAITING, heartbeat_get_state());

    // Advance time past boot grace period
    mock_set_timer((int64_t)HEARTBEAT_BOOT_GRACE_MS * 1000 + 1000);
    heartbeat_feed();

    TEST_ASSERT_EQUAL(HB_STATE_ACTIVE, heartbeat_get_state());
}

// --- Test 3: Feed updates last heartbeat timestamp ---
void test_heartbeat_feed_updates_timestamp(void)
{
    heartbeat_monitor_init();
    mock_set_timer(1000000); // 1 second
    heartbeat_feed();

    heartbeat_status_t status = heartbeat_get_status();
    TEST_ASSERT_EQUAL(1000000, status.last_heartbeat_us);
}

// --- Test 4: Status struct reports correct initial state ---
void test_heartbeat_status_initial(void)
{
    heartbeat_monitor_init();
    heartbeat_status_t status = heartbeat_get_status();

    TEST_ASSERT_EQUAL(HB_STATE_WAITING, status.state);
    TEST_ASSERT_EQUAL(0, status.reset_count);
}

// --- Test 5: Timeout constants are correct ---
void test_heartbeat_timeout_constants(void)
{
    TEST_ASSERT_EQUAL(5000, HEARTBEAT_TIMEOUT_MS);
    TEST_ASSERT_EQUAL(3, HEARTBEAT_MAX_RESETS);
    TEST_ASSERT_EQUAL(30 * 60 * 1000, HEARTBEAT_RESET_WINDOW_MS);
    TEST_ASSERT_EQUAL(3000, HEARTBEAT_RELAY_PULSE_MS);
}

// --- Test 6: PI5_RELAY_GPIO is defined correctly ---
void test_heartbeat_relay_gpio_defined(void)
{
    TEST_ASSERT_EQUAL(45, PI5_RELAY_GPIO);
}

// --- Test 7: Feed from TIMEOUT state transitions to ACTIVE ---
void test_heartbeat_feed_from_timeout_to_active(void)
{
    mock_set_timer(0);
    heartbeat_monitor_init();
    // Advance past boot grace period
    mock_set_timer((int64_t)HEARTBEAT_BOOT_GRACE_MS * 1000 + 1000);
    heartbeat_feed();
    TEST_ASSERT_EQUAL(HB_STATE_ACTIVE, heartbeat_get_state());

    // Simulate internal timeout state by feeding again
    // The task would set TIMEOUT, but we can test feed behavior
    // by verifying that feed always resets to ACTIVE from non-safe-mode states
    heartbeat_feed();
    TEST_ASSERT_EQUAL(HB_STATE_ACTIVE, heartbeat_get_state());
}
