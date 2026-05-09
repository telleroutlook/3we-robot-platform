// SPDX-License-Identifier: Apache-2.0
#ifndef OTA_SIGNING_H
#define OTA_SIGNING_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define OTA_SIGNATURE_SIZE      64  // ECDSA P-256 signature (r || s)
#define OTA_PUBKEY_SIZE         64  // ECDSA P-256 public key (X || Y, uncompressed without 0x04 prefix)
#define OTA_HASH_SIZE           32  // SHA-256 hash

// Firmware image header (prepended to binary)
typedef struct __attribute__((packed)) {
    uint32_t magic;             // 0x524F424F ("ROBO")
    uint32_t version;           // Semantic version packed: major.minor.patch
    uint32_t image_size;        // Size of firmware binary (excluding this header)
    uint8_t  sha256[OTA_HASH_SIZE];     // SHA-256 of firmware binary
    uint8_t  signature[OTA_SIGNATURE_SIZE]; // ECDSA P-256 signature (r || s) over sha256
    uint8_t  reserved[28];      // Future use, must be 0
} ota_image_header_t;

#define OTA_HEADER_MAGIC    0x524F424F

esp_err_t ota_signing_init(const uint8_t pubkey[OTA_PUBKEY_SIZE]);
bool ota_verify_image(const uint8_t *image_data, size_t image_size,
                      const ota_image_header_t *header);
bool ota_verify_image_hash(const uint8_t computed_hash[OTA_HASH_SIZE],
                           size_t image_size,
                           const ota_image_header_t *header);
esp_err_t ota_apply_update(const uint8_t *image_data, size_t total_size);
uint32_t ota_get_current_version(void);

#ifdef UNIT_TEST_BUILD
void ota_signing_reset_for_test(void);
#endif

#endif // OTA_SIGNING_H
