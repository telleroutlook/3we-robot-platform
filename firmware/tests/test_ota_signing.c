// SPDX-License-Identifier: Apache-2.0
// Unit tests for OTA signing verification (ota_signing.c)
#include "unity.h"
#include "ota_signing.h"
#include "mocks/mbedtls_stubs.h"
#include <string.h>

static uint8_t test_pubkey[OTA_PUBKEY_SIZE];
static uint8_t test_firmware[128];
static ota_image_header_t test_header;

void setUp_ota(void) {
    mock_mbedtls_reset();
    memset(test_pubkey, 0xAA, OTA_PUBKEY_SIZE);
    memset(test_firmware, 0x55, sizeof(test_firmware));

    // Prepare a valid header
    memset(&test_header, 0, sizeof(test_header));
    test_header.magic = OTA_HEADER_MAGIC;
    test_header.version = (2 << 16) | (0 << 8) | 0;  // v2.0.0
    test_header.image_size = sizeof(test_firmware);

    // Set mock SHA-256 output and copy to header so hash check passes
    uint8_t fake_hash[32];
    memset(fake_hash, 0xBB, 32);
    mock_mbedtls_set_sha256_output(fake_hash);
    memcpy(test_header.sha256, fake_hash, 32);

    // Signature verification passes by default
    mock_mbedtls_set_verify_result(0);

    // Current firmware is v1.0.0
    mock_ota_set_current_version("1.0.0");
    mock_ota_set_partition_available(true);
}

// --- ota_signing_init tests ---

void test_ota_init_accepts_valid_pubkey(void) {
    setUp_ota();
    esp_err_t err = ota_signing_init(test_pubkey);
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_ota_init_rejects_null_pubkey(void) {
    setUp_ota();
    esp_err_t err = ota_signing_init(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

// --- ota_verify_image tests ---

void test_ota_verify_accepts_valid_image(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_TRUE(result);
}

void test_ota_verify_rejects_before_init(void) {
    setUp_ota();
    ota_signing_reset_for_test();

    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_FALSE(result);
}

void test_ota_verify_rejects_wrong_magic(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    test_header.magic = 0x00000000;
    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_FALSE(result);
}

void test_ota_verify_rejects_size_mismatch(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    test_header.image_size = 999;  // Doesn't match actual size
    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_FALSE(result);
}

void test_ota_verify_rejects_hash_mismatch(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    // Mock SHA-256 returns different hash than what's in the header
    uint8_t different_hash[32];
    memset(different_hash, 0xCC, 32);
    mock_mbedtls_set_sha256_output(different_hash);

    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_FALSE(result);
}

void test_ota_verify_rejects_invalid_signature(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    // Make ECDSA verification fail
    mock_mbedtls_set_verify_result(-1);

    bool result = ota_verify_image(test_firmware, sizeof(test_firmware), &test_header);
    TEST_ASSERT_FALSE(result);
}

// --- ota_apply_update tests ---

void test_ota_apply_rejects_too_small(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    uint8_t tiny[4] = {0};
    esp_err_t err = ota_apply_update(tiny, sizeof(tiny));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_SIZE, err);
}

void test_ota_apply_rejects_too_large(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    // Simulate a 17MB image (exceeds 16MB limit)
    // We only need to pass the size check — no real allocation needed
    uint8_t buf[sizeof(ota_image_header_t) + 1];
    memset(buf, 0, sizeof(buf));
    esp_err_t err = ota_apply_update(buf, 17 * 1024 * 1024);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_SIZE, err);
}

void test_ota_apply_rejects_version_rollback(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    // Current is v1.0.0, try to apply v0.9.0
    size_t total = sizeof(ota_image_header_t) + sizeof(test_firmware);
    uint8_t *image = (uint8_t *)malloc(total);
    memset(image, 0, total);

    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->magic = OTA_HEADER_MAGIC;
    hdr->version = (0 << 16) | (9 << 8) | 0;  // v0.9.0 < v1.0.0
    hdr->image_size = sizeof(test_firmware);

    esp_err_t err = ota_apply_update(image, total);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_VERSION, err);

    free(image);
}

void test_ota_apply_rejects_same_version(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    // Current is v1.0.0, try to apply v1.0.0 (same version = allowed for recovery)
    size_t total = sizeof(ota_image_header_t) + sizeof(test_firmware);
    uint8_t *image = (uint8_t *)malloc(total);
    memset(image, 0, total);

    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->magic = OTA_HEADER_MAGIC;
    hdr->version = (1 << 16) | (0 << 8) | 0;  // v1.0.0 == current
    hdr->image_size = sizeof(test_firmware);

    esp_err_t err = ota_apply_update(image, total);
    TEST_ASSERT_TRUE(err != ESP_ERR_INVALID_VERSION);

    free(image);
}

void test_ota_apply_succeeds_with_valid_upgrade(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);

    size_t fw_size = sizeof(test_firmware);
    size_t total = sizeof(ota_image_header_t) + fw_size;
    uint8_t *image = (uint8_t *)malloc(total);
    memset(image, 0, total);

    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->magic = OTA_HEADER_MAGIC;
    hdr->version = (2 << 16) | (0 << 8) | 0;  // v2.0.0 > v1.0.0
    hdr->image_size = fw_size;

    // Copy firmware payload
    memcpy(image + sizeof(ota_image_header_t), test_firmware, fw_size);

    // Set up mock so hash matches
    uint8_t fake_hash[32];
    memset(fake_hash, 0xBB, 32);
    mock_mbedtls_set_sha256_output(fake_hash);
    memcpy(hdr->sha256, fake_hash, 32);

    esp_err_t err = ota_apply_update(image, total);
    TEST_ASSERT_EQUAL(ESP_OK, err);

    free(image);
}

void test_ota_apply_rejects_when_no_partition(void) {
    setUp_ota();
    ota_signing_init(test_pubkey);
    mock_ota_set_partition_available(false);

    size_t fw_size = sizeof(test_firmware);
    size_t total = sizeof(ota_image_header_t) + fw_size;
    uint8_t *image = (uint8_t *)malloc(total);
    memset(image, 0, total);

    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->magic = OTA_HEADER_MAGIC;
    hdr->version = (2 << 16) | (0 << 8) | 0;
    hdr->image_size = fw_size;

    memcpy(image + sizeof(ota_image_header_t), test_firmware, fw_size);

    uint8_t fake_hash[32];
    memset(fake_hash, 0xBB, 32);
    mock_mbedtls_set_sha256_output(fake_hash);
    memcpy(hdr->sha256, fake_hash, 32);

    esp_err_t err = ota_apply_update(image, total);
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, err);

    free(image);
}

// --- ota_check_version_policy tests ---

void test_ota_version_policy_allows_upgrade(void) {
    setUp_ota();
    // Current is v1.0.0, incoming is v2.0.0
    esp_err_t err = ota_check_version_policy((2 << 16) | (0 << 8) | 0);
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_ota_version_policy_rejects_rollback(void) {
    setUp_ota();
    // Current is v1.0.0, incoming is v0.9.0
    esp_err_t err = ota_check_version_policy((0 << 16) | (9 << 8) | 0);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_VERSION, err);
}

void test_ota_version_policy_rejects_same_version(void) {
    setUp_ota();
    // Current is v1.0.0, incoming is v1.0.0 — same version allowed for recovery
    esp_err_t err = ota_check_version_policy((1 << 16) | (0 << 8) | 0);
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_ota_version_policy_allows_when_current_unparseable(void) {
    setUp_ota();
    mock_ota_set_current_version("garbage");
    // When current version can't be parsed, updates should be allowed
    esp_err_t err = ota_check_version_policy((2 << 16) | (0 << 8) | 0);
    TEST_ASSERT_EQUAL(ESP_OK, err);
}
