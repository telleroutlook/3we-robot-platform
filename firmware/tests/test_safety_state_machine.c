// SPDX-License-Identifier: Apache-2.0
// Unit tests for safety state machine transitions (safety.c)
#include "unity.h"
#include "safety.h"

#define ESTOP_GPIO          41
#define SAFETY_RELAY_FB     42
#define SAFETY_RELAY_FB2    22
#define WATCHDOG_TIMEOUT_MS 1000

// --- Motor control mock ---
static int motor_stop_all_calls = 0;
void motor_stop_all(void) { motor_stop_all_calls++; }

// --- ISR deferred stop mocks ---
static bool mock_isr_stop_pending = false;
static int motor_clear_isr_stop_calls = 0;
bool motor_isr_stop_pending(void) { return mock_isr_stop_pending; }
void motor_clear_isr_stop(void) { motor_clear_isr_stop_calls++; mock_isr_stop_pending = false; }
void motor_stop_all_isr(void) { mock_isr_stop_pending = true; }

// --- Callback tracking ---
static int callback_invoked = 0;
static safety_state_t callback_last_state = SAFETY_NORMAL;

static void test_callback(safety_state_t state)
{
    callback_invoked++;
    callback_last_state = state;
}

// --- setUp: reset all state before each test ---
static void safety_test_setUp(void)
{
    motor_stop_all_calls = 0;
    mock_isr_stop_pending = false;
    motor_clear_isr_stop_calls = 0;
    callback_invoked = 0;
    callback_last_state = SAFETY_NORMAL;

    // Clear NVS mock state (prevents relay_fault key from leaking between tests)
    mock_nvs_reset();

    // GPIO 41 released (high = not pressed), relay feedback high (healthy)
    mock_set_gpio_level(ESTOP_GPIO, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 1);
    mock_set_timer(0);

    // Re-initialize safety module to reset static state
    safety_init();
}

// --- Test 1: Normal init with button released ---
void test_safety_init_normal(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_init();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}

// --- Test 2: Init with e-stop pressed at boot ---
void test_safety_init_estopped_at_boot(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 0);
    safety_init();
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 3: Trigger e-stop from NORMAL ---
void test_safety_trigger_estop_from_normal(void)
{
    safety_test_setUp();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
    safety_register_callback(test_callback);

    safety_trigger_estop();

    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
    TEST_ASSERT_EQUAL(1, motor_stop_all_calls);
    TEST_ASSERT_EQUAL(1, callback_invoked);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, callback_last_state);
}

// --- Test 4: Trigger e-stop when already stopped ---
void test_safety_trigger_estop_already_stopped(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    int calls_before = motor_stop_all_calls;

    safety_trigger_estop();

    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
    TEST_ASSERT_EQUAL(calls_before, motor_stop_all_calls);
}

// --- Test 5: is_estopped for all non-NORMAL states ---
void test_safety_is_estopped_all_non_normal(void)
{
    safety_test_setUp();
    // NORMAL — not estopped
    TEST_ASSERT_FALSE(safety_is_estopped());

    // ESTOPPED
    safety_trigger_estop();
    TEST_ASSERT_TRUE(safety_is_estopped());

    // RECOVERY_PENDING
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_reset();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());
    TEST_ASSERT_TRUE(safety_is_estopped());

    // RELAY_FAULT — reinit with fault condition
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_init();
    // Trigger 3 relay faults to escalate to RELAY_FAULT
    mock_set_gpio_level(SAFETY_RELAY_FB, 0);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 0);
    safety_relay_selftest();
    safety_relay_selftest();
    safety_relay_selftest();
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());
    TEST_ASSERT_TRUE(safety_is_estopped());
}

// --- Test 6: Reset success from ESTOPPED with GPIO high ---
void test_safety_reset_success(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 1);

    esp_err_t err = safety_reset();

    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());
}

// --- Test 7: Reset rejects when button still pressed ---
void test_safety_reset_rejects_button_pressed(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 0);

    esp_err_t err = safety_reset();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 8: Reset rejects from RELAY_FAULT state ---
void test_safety_reset_rejects_relay_fault(void)
{
    safety_test_setUp();
    // Force into RELAY_FAULT: 3 selftest failures
    mock_set_gpio_level(SAFETY_RELAY_FB, 0);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 0);
    safety_relay_selftest();
    safety_relay_selftest();
    safety_relay_selftest();
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());

    esp_err_t err = safety_reset();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());
}

// --- Test 9: Reset rejects from NORMAL state ---
void test_safety_reset_rejects_wrong_state(void)
{
    safety_test_setUp();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());

    esp_err_t err = safety_reset();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}

// --- Test 10: Confirm reset success ---
void test_safety_confirm_reset_success(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_reset();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());

    esp_err_t err = safety_confirm_reset();

    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}

// --- Test 11: Confirm reset rejects if button pressed during confirmation ---
void test_safety_confirm_reset_rejects_button_pressed(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 1);
    safety_reset();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());

    // Button goes low during confirmation
    mock_set_gpio_level(ESTOP_GPIO, 0);
    esp_err_t err = safety_confirm_reset();

    TEST_ASSERT_TRUE(err != ESP_OK);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 12: Confirm reset rejects from wrong state ---
void test_safety_confirm_reset_rejects_wrong_state(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());

    esp_err_t err = safety_confirm_reset();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 13: Watchdog timeout triggers e-stop ---
void test_safety_watchdog_timeout(void)
{
    safety_test_setUp();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
    safety_feed_watchdog();

    // Advance timer past timeout threshold
    mock_set_timer((int64_t)(WATCHDOG_TIMEOUT_MS + 1) * 1000);

    // Timeout is detected by safety_check_watchdog (called from safety_task)
    safety_check_watchdog();

    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 14: Feeding watchdog resets the timer ---
void test_safety_feed_watchdog_resets(void)
{
    safety_test_setUp();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());

    // Advance to just before timeout
    mock_set_timer((int64_t)(WATCHDOG_TIMEOUT_MS - 100) * 1000);
    safety_feed_watchdog();

    // Advance another small amount (total would exceed timeout from first feed,
    // but feed reset the window)
    mock_set_timer((int64_t)(WATCHDOG_TIMEOUT_MS + 800) * 1000);
    safety_feed_watchdog();

    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}

// --- Test 15: Relay selftest pass when released (GPIO41!=0, feedback HIGH) ---
void test_safety_relay_selftest_pass_released(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 1);

    esp_err_t err = safety_relay_selftest();

    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}

// --- Test 16: Relay selftest fail stuck off (GPIO41!=0, feedback LOW) ---
void test_safety_relay_selftest_fail_stuck_off(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB, 0);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 0);

    // Need 3 failures for RELAY_FAULT escalation
    safety_relay_selftest();
    safety_relay_selftest();
    esp_err_t err = safety_relay_selftest();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());
}

// --- Test 17: Relay selftest pass when pressed (GPIO41==0, feedback LOW) ---
void test_safety_relay_selftest_pass_pressed(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 0);
    safety_init(); // Will be ESTOPPED due to button pressed
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());

    mock_set_gpio_level(SAFETY_RELAY_FB, 0);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 0);

    esp_err_t err = safety_relay_selftest();

    TEST_ASSERT_EQUAL(ESP_OK, err);
}

// --- Test 18: Relay selftest fail welded (GPIO41==0, feedback HIGH) ---
void test_safety_relay_selftest_fail_welded(void)
{
    safety_test_setUp();
    mock_set_gpio_level(ESTOP_GPIO, 0);
    safety_init(); // ESTOPPED
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());

    mock_set_gpio_level(SAFETY_RELAY_FB, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 1);

    // Need 3 failures for escalation
    safety_relay_selftest();
    safety_relay_selftest();
    esp_err_t err = safety_relay_selftest();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());
}

// --- Test 19: Clear relay fault success ---
void test_safety_clear_relay_fault_success(void)
{
    safety_test_setUp();
    // Trigger RELAY_FAULT state
    mock_set_gpio_level(ESTOP_GPIO, 1);
    mock_set_gpio_level(SAFETY_RELAY_FB, 0);
    mock_set_gpio_level(SAFETY_RELAY_FB2, 0);
    safety_relay_selftest();
    safety_relay_selftest();
    safety_relay_selftest();
    TEST_ASSERT_EQUAL(SAFETY_RELAY_FAULT, safety_get_state());

    esp_err_t err = safety_clear_relay_fault();

    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
    TEST_ASSERT_FALSE(safety_is_relay_faulted());
}

// --- Test 20: Clear relay fault rejects from wrong state ---
void test_safety_clear_relay_fault_wrong_state(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());

    esp_err_t err = safety_clear_relay_fault();

    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
}

// --- Test 21: Callback invoked on e-stop trigger ---
void test_safety_callback_invoked_on_trigger(void)
{
    safety_test_setUp();
    safety_register_callback(test_callback);
    TEST_ASSERT_EQUAL(0, callback_invoked);

    safety_trigger_estop();

    TEST_ASSERT_EQUAL(1, callback_invoked);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, callback_last_state);
}

// --- Test 22: ISR deferred stop fires in safety loop ---
void test_isr_deferred_stop_fires_in_safety_loop(void)
{
    safety_test_setUp();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());

    // Simulate ISR setting the pending flag
    motor_stop_all_isr();
    TEST_ASSERT_TRUE(motor_isr_stop_pending());

    // Safety task loop iteration processes the deferred stop
    safety_process_deferred_stop();

    TEST_ASSERT_EQUAL(1, motor_stop_all_calls);
    TEST_ASSERT_EQUAL(1, motor_clear_isr_stop_calls);
    TEST_ASSERT_FALSE(motor_isr_stop_pending());
}

// --- Test 23: ISR deferred stop does not double-fire ---
void test_isr_deferred_stop_not_double_fired(void)
{
    safety_test_setUp();

    motor_stop_all_isr();
    safety_process_deferred_stop();
    TEST_ASSERT_EQUAL(1, motor_stop_all_calls);

    // Second iteration with flag already cleared
    safety_process_deferred_stop();
    TEST_ASSERT_EQUAL(1, motor_stop_all_calls);
    TEST_ASSERT_EQUAL(1, motor_clear_isr_stop_calls);
}

// --- Test 24: No stop when ISR flag not set ---
void test_isr_deferred_stop_noop_when_not_pending(void)
{
    safety_test_setUp();
    TEST_ASSERT_FALSE(motor_isr_stop_pending());

    safety_process_deferred_stop();

    TEST_ASSERT_EQUAL(0, motor_stop_all_calls);
    TEST_ASSERT_EQUAL(0, motor_clear_isr_stop_calls);
}

// --- Test 25: RECOVERY_PENDING times out to ESTOPPED ---
void test_safety_recovery_pending_timeout(void)
{
    safety_test_setUp();
    safety_register_callback(test_callback);
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 1);

    // Enter RECOVERY_PENDING
    mock_set_timer(1000000LL); // 1s
    safety_reset();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());
    callback_invoked = 0;

    // Not yet timed out (9s later)
    mock_set_timer(10000000LL); // 10s total
    safety_check_recovery_timeout();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());

    // Timed out (11s after entering RECOVERY_PENDING = 12s total)
    mock_set_timer(12000000LL); // 12s total, 11s since transition at 1s
    safety_check_recovery_timeout();
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, safety_get_state());
    TEST_ASSERT_EQUAL(1, callback_invoked);
    TEST_ASSERT_EQUAL(SAFETY_ESTOPPED, callback_last_state);
}

// --- Test 26: RECOVERY_PENDING timeout does not fire if confirmed in time ---
void test_safety_recovery_pending_no_timeout_if_confirmed(void)
{
    safety_test_setUp();
    safety_trigger_estop();
    mock_set_gpio_level(ESTOP_GPIO, 1);

    mock_set_timer(1000000LL);
    safety_reset();
    TEST_ASSERT_EQUAL(SAFETY_RECOVERY_PENDING, safety_get_state());

    // Confirm within timeout window
    mock_set_timer(5000000LL);
    safety_confirm_reset();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());

    // Even after timeout period, state remains NORMAL
    mock_set_timer(15000000LL);
    safety_check_recovery_timeout();
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, safety_get_state());
}
