// SPDX-License-Identifier: Apache-2.0
// Mock implementations for mbedtls and OTA partition APIs
#include "mbedtls_stubs.h"
#include "esp_stubs.h"
#include <string.h>

// --- Mock state ---
static int mock_verify_result = 0;  // 0 = success
static uint8_t mock_sha256[32] = {0};
static char mock_app_version[32] = "1.0.0";
static bool mock_partition_available = true;

void mock_mbedtls_set_verify_result(int result) { mock_verify_result = result; }

void mock_mbedtls_set_sha256_output(const uint8_t hash[32]) {
    memcpy(mock_sha256, hash, 32);
}

void mock_mbedtls_reset(void) {
    mock_verify_result = 0;
    memset(mock_sha256, 0, 32);
    strcpy(mock_app_version, "1.0.0");
    mock_partition_available = true;
}

void mock_ota_set_current_version(const char *version) {
    strncpy(mock_app_version, version, sizeof(mock_app_version) - 1);
    mock_app_version[sizeof(mock_app_version) - 1] = '\0';
}

void mock_ota_set_partition_available(bool available) {
    mock_partition_available = available;
}

// --- mbedtls bignum ---
void mbedtls_mpi_init(mbedtls_mpi *X) { memset(X, 0, sizeof(*X)); }
void mbedtls_mpi_free(mbedtls_mpi *X) { memset(X, 0, sizeof(*X)); }
int mbedtls_mpi_read_binary(mbedtls_mpi *X, const unsigned char *buf, size_t buflen) {
    (void)X; (void)buf; (void)buflen;
    return 0;
}

// --- mbedtls ECP ---
int mbedtls_ecp_group_load(mbedtls_ecp_group *grp, int id) {
    grp->id = id;
    return 0;
}

void mbedtls_ecp_group_init(mbedtls_ecp_group *grp) { memset(grp, 0, sizeof(*grp)); }
void mbedtls_ecp_group_free(mbedtls_ecp_group *grp) { memset(grp, 0, sizeof(*grp)); }
void mbedtls_ecp_point_init(mbedtls_ecp_point *pt) { memset(pt, 0, sizeof(*pt)); }
void mbedtls_ecp_point_free(mbedtls_ecp_point *pt) { memset(pt, 0, sizeof(*pt)); }

int mbedtls_ecp_point_read_binary(const mbedtls_ecp_group *grp, mbedtls_ecp_point *P,
                                   const unsigned char *buf, size_t ilen) {
    (void)grp; (void)P; (void)buf; (void)ilen;
    return 0;
}

// --- mbedtls ECDSA ---
void mbedtls_ecdsa_init(mbedtls_ecdsa_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }
void mbedtls_ecdsa_free(mbedtls_ecdsa_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }

int mbedtls_ecdsa_verify(mbedtls_ecp_group *grp, const unsigned char *buf, size_t blen,
                          const mbedtls_ecp_point *Q, const mbedtls_mpi *r, const mbedtls_mpi *s) {
    (void)grp; (void)buf; (void)blen; (void)Q; (void)r; (void)s;
    return mock_verify_result;
}

// --- mbedtls PK ---
static mbedtls_pk_info_t mock_pk_info = {0};

void mbedtls_pk_init(mbedtls_pk_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }
void mbedtls_pk_free(mbedtls_pk_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }

int mbedtls_pk_setup(mbedtls_pk_context *ctx, const mbedtls_pk_info_t *info) {
    ctx->pk_info = info;
    return 0;
}

const mbedtls_pk_info_t *mbedtls_pk_info_from_type(int pk_type) {
    (void)pk_type;
    return &mock_pk_info;
}

int mbedtls_pk_verify(mbedtls_pk_context *ctx, int md_alg,
                      const unsigned char *hash, size_t hash_len,
                      const unsigned char *sig, size_t sig_len) {
    (void)ctx; (void)md_alg; (void)hash; (void)hash_len; (void)sig; (void)sig_len;
    return mock_verify_result;
}

// --- mbedtls SHA-256 ---
void mbedtls_sha256_init(mbedtls_sha256_context *ctx) { (void)ctx; }
void mbedtls_sha256_free(mbedtls_sha256_context *ctx) { (void)ctx; }
int mbedtls_sha256_starts(mbedtls_sha256_context *ctx, int is224) { (void)ctx; (void)is224; return 0; }
int mbedtls_sha256_update(mbedtls_sha256_context *ctx, const unsigned char *input, size_t ilen) { (void)ctx; (void)input; (void)ilen; return 0; }
int mbedtls_sha256_finish(mbedtls_sha256_context *ctx, unsigned char *output) {
    (void)ctx;
    memcpy(output, mock_sha256, 32);
    return 0;
}
int mbedtls_sha256(const unsigned char *input, size_t ilen,
                   unsigned char *output, int is224) {
    (void)input; (void)ilen; (void)is224;
    memcpy(output, mock_sha256, 32);
    return 0;
}

// --- OTA partition mocks ---
static esp_partition_t mock_partition = {
    .label = "ota_0",
    .address = 0x100000,
    .size = 0x400000,
};

static esp_app_desc_t mock_app_desc;

const esp_partition_t *esp_ota_get_next_update_partition(const esp_partition_t *from) {
    (void)from;
    return mock_partition_available ? &mock_partition : NULL;
}

esp_err_t esp_ota_begin(const esp_partition_t *partition, size_t image_size, esp_ota_handle_t *handle) {
    (void)partition; (void)image_size;
    *handle = 1;
    return ESP_OK;
}

esp_err_t esp_ota_write(esp_ota_handle_t handle, const void *data, size_t size) {
    (void)handle; (void)data; (void)size;
    return ESP_OK;
}

esp_err_t esp_ota_end(esp_ota_handle_t handle) {
    (void)handle;
    return ESP_OK;
}

esp_err_t esp_ota_abort(esp_ota_handle_t handle) {
    (void)handle;
    return ESP_OK;
}

esp_err_t esp_ota_set_boot_partition(const esp_partition_t *partition) {
    (void)partition;
    return ESP_OK;
}

const esp_app_desc_t *esp_app_get_description(void) {
    strncpy(mock_app_desc.version, mock_app_version, sizeof(mock_app_desc.version) - 1);
    return &mock_app_desc;
}
