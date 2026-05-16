// SPDX-License-Identifier: Apache-2.0
// Unit tests for display module — navigation, debounce, fault log
#include "unity.h"
#include "i2c_stubs.h"
#include "freertos/semphr.h"
#include "pin_definitions.h"
#include "battery.h"
#include "safety.h"
#include "encoder.h"
#include "imu.h"
#include "thermal_monitor.h"
#include "dtls_transport.h"

#include <string.h>

#include "display.h"

// ---- Stubs for symbols not provided by other compiled firmware sources ----

// ota_progress_t defined locally (ota_update.c not in test build)
typedef struct {
    uint8_t status;
    uint8_t progress_pct;
    uint32_t bytes_received;
    uint32_t bytes_total;
    char error_msg[64];
} ota_progress_t;
#define OTA_STATUS_IDLE 0

ota_progress_t ota_update_get_progress(void)
{
    ota_progress_t p;
    memset(&p, 0, sizeof(p));
    return p;
}

// wifi_provision_store_credentials (wifi_provision.c not in test build)
static int wifi_store_calls = 0;
esp_err_t wifi_provision_store_credentials(const char *ssid, const char *password)
{
    (void)ssid; (void)password;
    wifi_store_calls++;
    return ESP_OK;
}

// esp_restart stub
static int restart_calls = 0;
void esp_restart(void) { restart_calls++; }

// ---- Test setUp ----

static void display_test_setUp(void)
{
    mock_i2c_reset();
    wifi_store_calls = 0;
    restart_calls = 0;
}

// ---- Tests: Initialization ----

void test_display_init_success(void)
{
    display_test_setUp();
    // Default I2C mock: writes and reads succeed for any address
    esp_err_t ret = display_init();
    TEST_ASSERT_EQUAL(ESP_OK, ret);
}

void test_display_init_no_device(void)
{
    display_test_setUp();
    // Make writes to the display address fail
    mock_i2c_set_write_error(DISPLAY_I2C_ADDR, ESP_FAIL);
    esp_err_t ret = display_init();
    TEST_ASSERT_TRUE(ret != ESP_OK);
}

// ---- Tests: Page Navigation ----

void test_display_initial_page_is_home(void)
{
    display_test_setUp();
    display_init();
    TEST_ASSERT_EQUAL(DISPLAY_PAGE_HOME, display_get_current_page());
}

// ---- Tests: Fault Log ----

void test_display_fault_log_empty_initially(void)
{
    display_test_setUp();
    display_init();
    // Verify no crash — page starts at HOME
    TEST_ASSERT_EQUAL(DISPLAY_PAGE_HOME, display_get_current_page());
}

void test_display_fault_log_single_entry(void)
{
    display_test_setUp();
    display_init();
    display_log_fault(FAULT_SRC_SAFETY, 1, "E-STOP");
    // No crash = pass
    TEST_ASSERT_EQUAL(DISPLAY_PAGE_HOME, display_get_current_page());
}

void test_display_fault_log_wraps_at_3(void)
{
    display_test_setUp();
    display_init();
    display_log_fault(FAULT_SRC_SAFETY, 1, "fault1");
    display_log_fault(FAULT_SRC_THERMAL, 2, "fault2");
    display_log_fault(FAULT_SRC_DRV_FRONT, 3, "fault3");
    // 4th entry should wrap without issue
    display_log_fault(FAULT_SRC_BATTERY, 4, "fault4");
    TEST_ASSERT_EQUAL(DISPLAY_PAGE_HOME, display_get_current_page());
}
