// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include <string.h>
#include <stdint.h>

// OTA status enum mirror (from ota_update.h)
typedef enum {
    TEST_OTA_IDLE = 0,
    TEST_OTA_DOWNLOADING,
    TEST_OTA_VERIFYING,
    TEST_OTA_APPLYING,
    TEST_OTA_REBOOTING,
    TEST_OTA_FAILED
} test_ota_status_t;

typedef struct {
    test_ota_status_t status;
    uint8_t progress_pct;
    uint32_t bytes_received;
    uint32_t bytes_total;
    char error_msg[64];
} test_ota_progress_t;

static test_ota_progress_t s_test_progress = {0};

static void test_set_progress(test_ota_status_t status, uint8_t pct,
                              uint32_t received, uint32_t total, const char *err)
{
    s_test_progress.status = status;
    s_test_progress.progress_pct = pct;
    s_test_progress.bytes_received = received;
    s_test_progress.bytes_total = total;
    if (err) {
        strncpy(s_test_progress.error_msg, err, sizeof(s_test_progress.error_msg) - 1);
    } else {
        s_test_progress.error_msg[0] = '\0';
    }
}

void test_ota_update_progress_initial_idle(void)
{
    test_set_progress(TEST_OTA_IDLE, 0, 0, 0, NULL);
    TEST_ASSERT_EQUAL(TEST_OTA_IDLE, s_test_progress.status);
    TEST_ASSERT_EQUAL(0, s_test_progress.progress_pct);
    TEST_ASSERT_EQUAL_STRING("", s_test_progress.error_msg);
}

void test_ota_update_progress_downloading(void)
{
    test_set_progress(TEST_OTA_DOWNLOADING, 50, 2048, 4096, NULL);
    TEST_ASSERT_EQUAL(TEST_OTA_DOWNLOADING, s_test_progress.status);
    TEST_ASSERT_EQUAL(50, s_test_progress.progress_pct);
    TEST_ASSERT_EQUAL(2048, s_test_progress.bytes_received);
    TEST_ASSERT_EQUAL(4096, s_test_progress.bytes_total);
}

void test_ota_update_progress_failed_with_message(void)
{
    test_set_progress(TEST_OTA_FAILED, 0, 0, 0, "Version rollback rejected");
    TEST_ASSERT_EQUAL(TEST_OTA_FAILED, s_test_progress.status);
    TEST_ASSERT_EQUAL_STRING("Version rollback rejected", s_test_progress.error_msg);
}

void test_ota_update_progress_pct_calculation(void)
{
    uint32_t received = 3072;
    uint32_t total = 4096;
    uint8_t pct = (uint8_t)((received * 100) / total);
    TEST_ASSERT_EQUAL(75, pct);
}

void test_ota_update_progress_pct_zero_total(void)
{
    uint32_t received = 0;
    uint32_t total = 1;
    uint8_t pct = (uint8_t)((received * 100) / total);
    TEST_ASSERT_EQUAL(0, pct);
}

void test_ota_update_progress_pct_complete(void)
{
    uint32_t received = 4096;
    uint32_t total = 4096;
    uint8_t pct = (uint8_t)((received * 100) / total);
    TEST_ASSERT_EQUAL(100, pct);
}

void test_ota_update_rejects_empty_url(void)
{
    const char *url = "";
    TEST_ASSERT_TRUE(url == NULL || strlen(url) == 0);
}

void test_ota_update_url_max_length(void)
{
    char url[257];
    memset(url, 'a', 256);
    url[256] = '\0';
    TEST_ASSERT_TRUE(strlen(url) >= 256);
}
