// SPDX-License-Identifier: Apache-2.0
// Mock mbedtls types and functions for OTA/DTLS unit testing
#ifndef MBEDTLS_STUBS_H
#define MBEDTLS_STUBS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>

// --- mbedtls bignum ---
typedef struct { int s; size_t n; uint32_t *p; } mbedtls_mpi;
void mbedtls_mpi_init(mbedtls_mpi *X);
void mbedtls_mpi_free(mbedtls_mpi *X);
int mbedtls_mpi_read_binary(mbedtls_mpi *X, const unsigned char *buf, size_t buflen);

// --- mbedtls ECP ---
#define MBEDTLS_ECP_DP_SECP256R1 0

typedef struct { int id; } mbedtls_ecp_group;
typedef struct { mbedtls_mpi X; mbedtls_mpi Y; mbedtls_mpi Z; } mbedtls_ecp_point;

int mbedtls_ecp_group_load(mbedtls_ecp_group *grp, int id);
int mbedtls_ecp_point_read_binary(const mbedtls_ecp_group *grp, mbedtls_ecp_point *P,
                                   const unsigned char *buf, size_t ilen);

// --- mbedtls ECDSA ---
typedef struct {
    mbedtls_ecp_group grp;
    mbedtls_ecp_point Q;
    mbedtls_mpi d;
} mbedtls_ecdsa_context;

void mbedtls_ecdsa_init(mbedtls_ecdsa_context *ctx);
void mbedtls_ecdsa_free(mbedtls_ecdsa_context *ctx);
int mbedtls_ecdsa_verify(mbedtls_ecp_group *grp, const unsigned char *buf, size_t blen,
                          const mbedtls_ecp_point *Q, const mbedtls_mpi *r, const mbedtls_mpi *s);

// --- mbedtls SHA-256 ---
int mbedtls_sha256(const unsigned char *input, size_t ilen,
                   unsigned char *output, int is224);

// --- Mock control ---
void mock_mbedtls_set_verify_result(int result);
void mock_mbedtls_set_sha256_output(const uint8_t hash[32]);
void mock_mbedtls_reset(void);

// --- OTA partition mocks ---
typedef struct {
    const char *label;
    uint32_t address;
    uint32_t size;
} esp_partition_t;

typedef int esp_ota_handle_t;

typedef struct {
    char version[32];
} esp_app_desc_t;

const esp_partition_t *esp_ota_get_next_update_partition(const esp_partition_t *from);
esp_err_t esp_ota_begin(const esp_partition_t *partition, size_t image_size, esp_ota_handle_t *handle);
esp_err_t esp_ota_write(esp_ota_handle_t handle, const void *data, size_t size);
esp_err_t esp_ota_end(esp_ota_handle_t handle);
esp_err_t esp_ota_abort(esp_ota_handle_t handle);
esp_err_t esp_ota_set_boot_partition(const esp_partition_t *partition);
const esp_app_desc_t *esp_app_get_description(void);

#define ESP_ERR_INVALID_SIZE   0x0105
#define ESP_ERR_INVALID_VERSION 0x0106
#define ESP_ERR_NOT_FOUND      0x0107

void mock_ota_set_current_version(const char *version);
void mock_ota_set_partition_available(bool available);

#endif // MBEDTLS_STUBS_H
