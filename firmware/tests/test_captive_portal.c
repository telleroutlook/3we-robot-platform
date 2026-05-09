// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include <string.h>
#include <stdint.h>

// Mocked NVS state
static char mock_nvs_ssid[64] = {0};
static char mock_nvs_pass[64] = {0};
static int mock_nvs_store_calls = 0;

// Mock wifi_provision_store_credentials for testing
int mock_wifi_store(const char *ssid, const char *password)
{
    if (!ssid || strlen(ssid) == 0) return -1;
    strncpy(mock_nvs_ssid, ssid, sizeof(mock_nvs_ssid) - 1);
    strncpy(mock_nvs_pass, password ? password : "", sizeof(mock_nvs_pass) - 1);
    mock_nvs_store_calls++;
    return 0;
}

static void reset_captive_portal_mocks(void)
{
    memset(mock_nvs_ssid, 0, sizeof(mock_nvs_ssid));
    memset(mock_nvs_pass, 0, sizeof(mock_nvs_pass));
    mock_nvs_store_calls = 0;
}

// Test: SSID generation from MAC bytes
void test_captive_portal_ssid_from_mac(void)
{
    uint8_t mac[6] = {0x11, 0x22, 0x33, 0x44, 0xAB, 0xCD};
    char ssid[32];
    snprintf(ssid, sizeof(ssid), "RobotPlatform_%02X%02X", mac[4], mac[5]);
    TEST_ASSERT_EQUAL_STRING("RobotPlatform_ABCD", ssid);
}

// Test: SSID generation with zero MAC
void test_captive_portal_ssid_zero_mac(void)
{
    uint8_t mac[6] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
    char ssid[32];
    snprintf(ssid, sizeof(ssid), "RobotPlatform_%02X%02X", mac[4], mac[5]);
    TEST_ASSERT_EQUAL_STRING("RobotPlatform_0000", ssid);
}

// Test: credential store rejects empty SSID
void test_captive_portal_store_rejects_empty_ssid(void)
{
    reset_captive_portal_mocks();
    int ret = mock_wifi_store("", "password");
    TEST_ASSERT_EQUAL(-1, ret);
    TEST_ASSERT_EQUAL(0, mock_nvs_store_calls);
}

// Test: credential store rejects NULL SSID
void test_captive_portal_store_rejects_null_ssid(void)
{
    reset_captive_portal_mocks();
    int ret = mock_wifi_store(NULL, "password");
    TEST_ASSERT_EQUAL(-1, ret);
    TEST_ASSERT_EQUAL(0, mock_nvs_store_calls);
}

// Test: credential store accepts valid SSID
void test_captive_portal_store_accepts_valid(void)
{
    reset_captive_portal_mocks();
    int ret = mock_wifi_store("TestNetwork", "secret123");
    TEST_ASSERT_EQUAL(0, ret);
    TEST_ASSERT_EQUAL(1, mock_nvs_store_calls);
    TEST_ASSERT_EQUAL_STRING("TestNetwork", mock_nvs_ssid);
    TEST_ASSERT_EQUAL_STRING("secret123", mock_nvs_pass);
}

// Test: credential store handles empty password (open network)
void test_captive_portal_store_empty_password(void)
{
    reset_captive_portal_mocks();
    int ret = mock_wifi_store("OpenNet", "");
    TEST_ASSERT_EQUAL(0, ret);
    TEST_ASSERT_EQUAL_STRING("OpenNet", mock_nvs_ssid);
    TEST_ASSERT_EQUAL_STRING("", mock_nvs_pass);
}

// Test: credential store handles NULL password
void test_captive_portal_store_null_password(void)
{
    reset_captive_portal_mocks();
    int ret = mock_wifi_store("OpenNet", NULL);
    TEST_ASSERT_EQUAL(0, ret);
    TEST_ASSERT_EQUAL_STRING("OpenNet", mock_nvs_ssid);
    TEST_ASSERT_EQUAL_STRING("", mock_nvs_pass);
}
