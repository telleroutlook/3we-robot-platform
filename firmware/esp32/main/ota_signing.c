// SPDX-License-Identifier: Apache-2.0
#include "ota_signing.h"

#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "mbedtls/sha256.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/ecp.h"
#include "mbedtls/md.h"
#include "mbedtls/error.h"
#include "mbedtls/bignum.h"

#include <string.h>
#include <stdio.h>
#include <stdint.h>

#include "nvs_flash.h"
#include "nvs.h"

static const char *TAG = "ota_sign";

static uint8_t stored_pubkey[OTA_PUBKEY_SIZE];
static bool initialized = false;
static char ota_upload_token[65] = {0};

static int constant_time_compare(const void *a, const void *b, size_t len)
{
    const volatile uint8_t *x = (const volatile uint8_t *)a;
    const volatile uint8_t *y = (const volatile uint8_t *)b;
    volatile uint8_t diff = 0;
    for (size_t i = 0; i < len; i++) {
        diff |= x[i] ^ y[i];
    }
    return diff == 0;
}

bool ota_signing_check_upload_token(const char *auth_header)
{
    if (!auth_header || ota_upload_token[0] == '\0') return false;

    const char *prefix = "Bearer ";
    size_t prefix_len = 7;
    if (strncmp(auth_header, prefix, prefix_len) != 0) return false;

    const char *token = auth_header + prefix_len;
    size_t token_len = strlen(token);
    size_t expected_len = strlen(ota_upload_token);
    if (token_len != expected_len) return false;

    return constant_time_compare(token, ota_upload_token, expected_len);
}

static bool ecdsa_p256_verify(const uint8_t *hash, size_t hash_len,
                              const uint8_t *signature, const uint8_t *pubkey)
{
    int ret;
    mbedtls_ecp_group grp;
    mbedtls_ecp_point Q;
    mbedtls_mpi r, s;

    mbedtls_ecp_group_init(&grp);
    mbedtls_ecp_point_init(&Q);
    mbedtls_mpi_init(&r);
    mbedtls_mpi_init(&s);

    ret = mbedtls_ecp_group_load(&grp, MBEDTLS_ECP_DP_SECP256R1);
    if (ret != 0) {
        ESP_LOGE(TAG, "ecp_group_load P-256 failed: -0x%04X", (unsigned int)-ret);
        goto cleanup;
    }

    // Load uncompressed public key (0x04 || X || Y = 65 bytes)
    uint8_t uncompressed[65];
    uncompressed[0] = 0x04;
    memcpy(&uncompressed[1], pubkey, OTA_PUBKEY_SIZE);

    ret = mbedtls_ecp_point_read_binary(&grp, &Q,
                                         uncompressed, sizeof(uncompressed));
    if (ret != 0) {
        ESP_LOGE(TAG, "point_read_binary failed: -0x%04X", (unsigned int)-ret);
        goto cleanup;
    }

    // Parse raw r||s (32 bytes each) into mpi
    ret = mbedtls_mpi_read_binary(&r, signature, 32);
    if (ret == 0) {
        ret = mbedtls_mpi_read_binary(&s, signature + 32, 32);
    }
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to parse signature: -0x%04X", (unsigned int)-ret);
        goto cleanup;
    }

    ret = mbedtls_ecdsa_verify(&grp, hash, hash_len, &Q, &r, &s);
    if (ret != 0) {
        ESP_LOGW(TAG, "Signature verification failed: -0x%04X", (unsigned int)-ret);
    }

cleanup:
    mbedtls_mpi_free(&s);
    mbedtls_mpi_free(&r);
    mbedtls_ecp_point_free(&Q);
    mbedtls_ecp_group_free(&grp);
    return ret == 0;
}

esp_err_t ota_signing_init(const uint8_t pubkey[OTA_PUBKEY_SIZE])
{
    if (!pubkey) return ESP_ERR_INVALID_ARG;
    memcpy(stored_pubkey, pubkey, OTA_PUBKEY_SIZE);

    // Load upload token from NVS
    nvs_handle_t nvs;
    if (nvs_open("ota", NVS_READONLY, &nvs) == ESP_OK) {
        size_t len = sizeof(ota_upload_token) - 1;
        if (nvs_get_str(nvs, "upload_token", ota_upload_token, &len) != ESP_OK) {
            ota_upload_token[0] = '\0';
        }
        nvs_close(nvs);
    }

    if (ota_upload_token[0] == '\0') {
        ESP_LOGW(TAG, "OTA upload token not provisioned - /ota/upload endpoint is disabled");
    }

    initialized = true;
    ESP_LOGI(TAG, "OTA signing initialized (ECDSA P-256 pubkey loaded)");
    return ESP_OK;
}

bool ota_verify_image(const uint8_t *image_data, size_t image_size,
                      const ota_image_header_t *header)
{
    if (!initialized) {
        ESP_LOGE(TAG, "Not initialized - rejecting image");
        return false;
    }

    uint8_t computed_hash[OTA_HASH_SIZE];
    mbedtls_sha256(image_data, image_size, computed_hash, 0);

    return ota_verify_image_hash(computed_hash, image_size, header);
}

bool ota_verify_image_hash(const uint8_t computed_hash[OTA_HASH_SIZE],
                           size_t image_size,
                           const ota_image_header_t *header)
{
    if (!initialized) {
        ESP_LOGE(TAG, "Not initialized - rejecting image");
        return false;
    }

    if (header->magic != OTA_HEADER_MAGIC) {
        ESP_LOGE(TAG, "Invalid magic: 0x%08lX", (unsigned long)header->magic);
        return false;
    }

    if (header->image_size != image_size) {
        ESP_LOGE(TAG, "Size mismatch: header=%lu, actual=%zu",
                 (unsigned long)header->image_size, image_size);
        return false;
    }

    // Verify hash matches header
    if (memcmp(computed_hash, header->sha256, OTA_HASH_SIZE) != 0) {
        ESP_LOGE(TAG, "SHA-256 hash mismatch - image corrupted");
        return false;
    }

    // Compute signed digest: SHA-256(magic || version || image_size || firmware_hash)
    uint8_t signed_digest[OTA_HASH_SIZE];
    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);
    mbedtls_sha256_update(&sha_ctx, (const uint8_t *)&header->magic, sizeof(header->magic));
    mbedtls_sha256_update(&sha_ctx, (const uint8_t *)&header->version, sizeof(header->version));
    mbedtls_sha256_update(&sha_ctx, (const uint8_t *)&header->image_size, sizeof(header->image_size));
    mbedtls_sha256_update(&sha_ctx, computed_hash, OTA_HASH_SIZE);
    mbedtls_sha256_finish(&sha_ctx, signed_digest);
    mbedtls_sha256_free(&sha_ctx);

    // Verify ECDSA P-256 signature over the bound digest
    if (!ecdsa_p256_verify(signed_digest, OTA_HASH_SIZE,
                        header->signature, stored_pubkey)) {
        ESP_LOGE(TAG, "ECDSA P-256 signature verification FAILED - rejecting image");
        return false;
    }

    ESP_LOGI(TAG, "Image verified: size=%zu, version=0x%08lX",
             image_size, (unsigned long)header->version);
    return true;
}

esp_err_t ota_apply_update(const uint8_t *image_data, size_t total_size)
{
    if (total_size <= sizeof(ota_image_header_t)) {
        return ESP_ERR_INVALID_SIZE;
    }

    // Reject unreasonably large images (16 MB max for ESP32 flash)
    if (total_size > (16 * 1024 * 1024)) {
        ESP_LOGE(TAG, "Image too large: %zu bytes", total_size);
        return ESP_ERR_INVALID_SIZE;
    }

    const ota_image_header_t *header = (const ota_image_header_t *)image_data;
    const uint8_t *firmware = image_data + sizeof(ota_image_header_t);
    size_t firmware_size = total_size - sizeof(ota_image_header_t);

    // Reject version downgrades
    esp_err_t ver_err = ota_check_version_policy(header->version);
    if (ver_err != ESP_OK) {
        return ver_err;
    }

    // Verify signature before writing
    if (!ota_verify_image(firmware, firmware_size, header)) {
        ESP_LOGE(TAG, "Verification failed - aborting OTA");
        return ESP_ERR_INVALID_STATE;
    }

    // Find OTA partition and write
    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    if (!update_partition) {
        ESP_LOGE(TAG, "No OTA partition available");
        return ESP_ERR_NOT_FOUND;
    }

    esp_ota_handle_t ota_handle;
    esp_err_t err = esp_ota_begin(update_partition, firmware_size, &ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "OTA begin failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_ota_write(ota_handle, firmware, firmware_size);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "OTA write failed: %s", esp_err_to_name(err));
        esp_ota_abort(ota_handle);
        return err;
    }

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "OTA end failed: %s", esp_err_to_name(err));
        return err;
    }

    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Set boot partition failed: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "OTA update applied successfully - reboot to activate");
    return ESP_OK;
}

uint32_t ota_get_current_version(void)
{
    const esp_app_desc_t *app_desc = esp_app_get_description();
    int major = 0, minor = 0, patch = 0;
    int n = sscanf(app_desc->version, "%d.%d.%d", &major, &minor, &patch);
    if (n != 3 || major < 0 || major > 255 ||
        minor < 0 || minor > 255 || patch < 0 || patch > 255) {
        ESP_LOGW(TAG, "Could not parse version string '%s'", app_desc->version);
        return UINT32_MAX;
    }
    return ((uint32_t)major << 16) | ((uint32_t)minor << 8) | (uint32_t)patch;
}

esp_err_t ota_check_version_policy(uint32_t incoming_version)
{
    uint32_t current = ota_get_current_version();
    if (current == UINT32_MAX) {
        ESP_LOGW(TAG, "Cannot determine current version - allowing update");
        return ESP_OK;
    }
    if (incoming_version <= current) {
        ESP_LOGE(TAG, "Version rollback rejected: incoming=0x%08lX, current=0x%08lX",
                 (unsigned long)incoming_version, (unsigned long)current);
        return ESP_ERR_INVALID_VERSION;
    }
    return ESP_OK;
}

#ifdef UNIT_TEST_BUILD
void ota_signing_reset_for_test(void)
{
    initialized = false;
    memset(stored_pubkey, 0, OTA_PUBKEY_SIZE);
}
#endif
