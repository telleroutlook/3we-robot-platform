// SPDX-License-Identifier: Apache-2.0
#include "ota_signing.h"

#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "mbedtls/sha256.h"

// Ed25519 verification using libsodium-style or tweetnacl
// ESP-IDF includes mbedtls which supports Ed25519 via ECDSA alt
// For pure Ed25519, we use a minimal implementation
#include "mbedtls/md.h"
#include "mbedtls/pk.h"

#include <string.h>

static const char *TAG = "ota_sign";

static uint8_t stored_pubkey[OTA_PUBKEY_SIZE];
static bool initialized = false;

// Minimal Ed25519 verify (using mbedtls ECDSA with Edwards curve)
// In production, use esp_secure_boot APIs or dedicated Ed25519 lib
static bool ed25519_verify(const uint8_t *message, size_t msg_len,
                           const uint8_t *signature, const uint8_t *pubkey)
{
    // ESP-IDF secure boot v2 uses RSA-PSS or ECDSA-256 natively.
    // For Ed25519 specifically, the recommended approach is:
    // 1. Use esp_secure_boot (hardware verified boot) in production
    // 2. For application-level OTA verification, use a bundled Ed25519 lib
    //
    // This is a placeholder that demonstrates the verification flow.
    // Replace with actual Ed25519 verify when integrating a crypto library
    // (e.g., micro-ecc, tweetnacl, or libsodium)
    //
    // SECURITY NOTE: This placeholder always returns false to prevent
    // accepting unsigned images. A real implementation must be provided.

    (void)message;
    (void)msg_len;
    (void)signature;
    (void)pubkey;

    ESP_LOGW(TAG, "Ed25519 verify placeholder - integrate actual crypto lib");
    return false;
}

esp_err_t ota_signing_init(const uint8_t pubkey[OTA_PUBKEY_SIZE])
{
    if (!pubkey) return ESP_ERR_INVALID_ARG;
    memcpy(stored_pubkey, pubkey, OTA_PUBKEY_SIZE);
    initialized = true;
    ESP_LOGI(TAG, "OTA signing initialized (Ed25519 pubkey loaded)");
    return ESP_OK;
}

bool ota_verify_image(const uint8_t *image_data, size_t image_size,
                      const ota_image_header_t *header)
{
    if (!initialized) {
        ESP_LOGE(TAG, "Not initialized - rejecting image");
        return false;
    }

    // Verify magic
    if (header->magic != OTA_HEADER_MAGIC) {
        ESP_LOGE(TAG, "Invalid magic: 0x%08lX", (unsigned long)header->magic);
        return false;
    }

    // Verify image size matches
    if (header->image_size != image_size) {
        ESP_LOGE(TAG, "Size mismatch: header=%lu, actual=%zu",
                 (unsigned long)header->image_size, image_size);
        return false;
    }

    // Compute SHA-256 of image
    uint8_t computed_hash[OTA_HASH_SIZE];
    mbedtls_sha256(image_data, image_size, computed_hash, 0);

    // Verify hash matches header
    if (memcmp(computed_hash, header->sha256, OTA_HASH_SIZE) != 0) {
        ESP_LOGE(TAG, "SHA-256 hash mismatch - image corrupted");
        return false;
    }

    // Verify Ed25519 signature over the hash
    if (!ed25519_verify(computed_hash, OTA_HASH_SIZE,
                        header->signature, stored_pubkey)) {
        ESP_LOGE(TAG, "Ed25519 signature verification FAILED - rejecting image");
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

    const ota_image_header_t *header = (const ota_image_header_t *)image_data;
    const uint8_t *firmware = image_data + sizeof(ota_image_header_t);
    size_t firmware_size = total_size - sizeof(ota_image_header_t);

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
    // Version stored in app description
    const esp_app_desc_t *app_desc = esp_app_get_description();
    // Parse version string "x.y.z" to packed uint32
    int major = 0, minor = 0, patch = 0;
    sscanf(app_desc->version, "%d.%d.%d", &major, &minor, &patch);
    return (major << 16) | (minor << 8) | patch;
}
