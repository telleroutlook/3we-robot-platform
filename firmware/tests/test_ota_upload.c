// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "ota_signing.h"

#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

// --- Mock HTTP server layer ---

#define HTTPD_400_BAD_REQUEST   400
#define HTTPD_500_INTERNAL_SERVER_ERROR 500

typedef struct {
    size_t content_len;
    const uint8_t *body;
    size_t body_pos;
} mock_httpd_req_t;

static int mock_http_status;
static char mock_http_error[128];
static char mock_http_response[256];
static char mock_http_content_type[64];

static void mock_httpd_resp_send_err(mock_httpd_req_t *req, int status, const char *msg)
{
    (void)req;
    mock_http_status = status;
    strncpy(mock_http_error, msg, sizeof(mock_http_error) - 1);
}

static void mock_httpd_resp_set_type(mock_httpd_req_t *req, const char *type)
{
    (void)req;
    strncpy(mock_http_content_type, type, sizeof(mock_http_content_type) - 1);
}

static void mock_httpd_resp_send(mock_httpd_req_t *req, const char *body, int len)
{
    (void)req; (void)len;
    if (body) strncpy(mock_http_response, body, sizeof(mock_http_response) - 1);
}

static int mock_httpd_req_recv(mock_httpd_req_t *req, char *buf, int len)
{
    if (!req->body || req->body_pos >= req->content_len) return 0;
    size_t avail = req->content_len - req->body_pos;
    size_t to_copy = (size_t)len < avail ? (size_t)len : avail;
    memcpy(buf, req->body + req->body_pos, to_copy);
    req->body_pos += to_copy;
    return (int)to_copy;
}

// --- Mock OTA partition layer ---

#define OTA_BUF_SIZE       4096
#define OTA_MAX_IMAGE_SIZE (4 * 1024 * 1024)

static bool mock_ota_begin_fail;
static bool mock_ota_write_fail;
static bool mock_ota_end_fail;
static bool mock_ota_set_boot_fail;
static bool mock_no_partition;
static bool mock_verify_hash_result;
static uint8_t mock_ota_written[8192];
static size_t mock_ota_written_len;

static esp_partition_t mock_partition;

static const esp_partition_t *mock_esp_ota_get_next_update_partition(void *unused)
{
    (void)unused;
    return mock_no_partition ? NULL : &mock_partition;
}

static esp_err_t mock_esp_ota_begin(const esp_partition_t *part, size_t size, esp_ota_handle_t *handle)
{
    (void)part; (void)size;
    *handle = 1;
    return mock_ota_begin_fail ? ESP_FAIL : ESP_OK;
}

static esp_err_t mock_esp_ota_write(esp_ota_handle_t handle, const void *data, size_t len)
{
    (void)handle;
    if (mock_ota_write_fail) return ESP_FAIL;
    if (mock_ota_written_len + len <= sizeof(mock_ota_written)) {
        memcpy(mock_ota_written + mock_ota_written_len, data, len);
        mock_ota_written_len += len;
    }
    return ESP_OK;
}

static esp_err_t mock_esp_ota_end(esp_ota_handle_t handle)
{
    (void)handle;
    return mock_ota_end_fail ? ESP_FAIL : ESP_OK;
}

static void mock_esp_ota_abort(esp_ota_handle_t handle) { (void)handle; }

static esp_err_t mock_esp_ota_set_boot_partition(const esp_partition_t *part)
{
    (void)part;
    return mock_ota_set_boot_fail ? ESP_FAIL : ESP_OK;
}

static bool mock_ota_verify_image_hash(const uint8_t *hash, size_t size, const ota_image_header_t *hdr)
{
    (void)hash; (void)size; (void)hdr;
    return mock_verify_hash_result;
}

// --- Minimal re-implementation of handler_ota_upload for testability ---
// This mirrors the logic from ota_update.c handler_ota_upload

typedef enum {
    OTA_STATUS_IDLE = 0,
    OTA_STATUS_DOWNLOADING,
    OTA_STATUS_VERIFYING,
    OTA_STATUS_APPLYING,
    OTA_STATUS_REBOOTING,
    OTA_STATUS_FAILED
} ota_status_t;

static ota_status_t mock_last_status;
static char mock_last_error[64];
static bool mock_reboot_called;

static void mock_set_progress(ota_status_t status, uint8_t pct,
                              uint32_t received, uint32_t total, const char *err)
{
    (void)pct; (void)received; (void)total;
    mock_last_status = status;
    if (err) strncpy(mock_last_error, err, sizeof(mock_last_error) - 1);
    else mock_last_error[0] = '\0';
}

static esp_err_t testable_handler_ota_upload(mock_httpd_req_t *req)
{
    if (req->content_len == 0 || req->content_len > OTA_MAX_IMAGE_SIZE) {
        mock_httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid size");
        return ESP_FAIL;
    }

    uint8_t *buf = malloc(OTA_BUF_SIZE);
    if (!buf) {
        mock_httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Out of memory");
        return ESP_FAIL;
    }

    int ret = mock_httpd_req_recv(req, (char *)buf, sizeof(ota_image_header_t));
    if (ret != (int)sizeof(ota_image_header_t)) {
        free(buf);
        mock_httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Failed to read header");
        return ESP_FAIL;
    }

    ota_image_header_t header;
    memcpy(&header, buf, sizeof(header));

    if (header.magic != OTA_HEADER_MAGIC) {
        free(buf);
        mock_httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid image magic");
        return ESP_FAIL;
    }

    uint32_t firmware_size = header.image_size;
    if (firmware_size == 0 || firmware_size > OTA_MAX_IMAGE_SIZE) {
        free(buf);
        mock_httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid firmware size in header");
        return ESP_FAIL;
    }

    const esp_partition_t *update_part = mock_esp_ota_get_next_update_partition(NULL);
    if (!update_part) {
        free(buf);
        mock_httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "No OTA partition");
        return ESP_FAIL;
    }

    esp_ota_handle_t ota_handle;
    esp_err_t err = mock_esp_ota_begin(update_part, firmware_size, &ota_handle);
    if (err != ESP_OK) {
        free(buf);
        mock_httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "OTA begin failed");
        return ESP_FAIL;
    }

    mock_set_progress(OTA_STATUS_DOWNLOADING, 0, 0, firmware_size, NULL);

    uint32_t firmware_written = 0;
    bool upload_ok = true;

    while (firmware_written < firmware_size) {
        int to_read = (int)((firmware_size - firmware_written) < OTA_BUF_SIZE ?
                            (firmware_size - firmware_written) : OTA_BUF_SIZE);
        ret = mock_httpd_req_recv(req, (char *)buf, to_read);
        if (ret <= 0) {
            upload_ok = false;
            break;
        }

        err = mock_esp_ota_write(ota_handle, buf, (size_t)ret);
        if (err != ESP_OK) {
            upload_ok = false;
            break;
        }

        firmware_written += (uint32_t)ret;
    }

    free(buf);

    if (!upload_ok || firmware_written != firmware_size) {
        mock_esp_ota_abort(ota_handle);
        mock_set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Upload incomplete");
        mock_httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Upload incomplete");
        return ESP_FAIL;
    }

    mock_set_progress(OTA_STATUS_VERIFYING, 100, firmware_written, firmware_size, NULL);

    uint8_t computed_hash[OTA_HASH_SIZE];
    memset(computed_hash, 0xAA, OTA_HASH_SIZE);

    if (!mock_ota_verify_image_hash(computed_hash, firmware_size, &header)) {
        mock_esp_ota_abort(ota_handle);
        mock_set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Signature verification failed");
        mock_httpd_resp_set_type(req, "application/json");
        mock_httpd_resp_send(req, "{\"success\":false,\"error\":\"Signature verification failed\"}", -1);
        return ESP_FAIL;
    }

    err = mock_esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        mock_esp_ota_abort(ota_handle);
        mock_set_progress(OTA_STATUS_FAILED, 0, 0, 0, "OTA end failed");
        mock_httpd_resp_set_type(req, "application/json");
        mock_httpd_resp_send(req, "{\"success\":false,\"error\":\"OTA finalize failed\"}", -1);
        return ESP_FAIL;
    }

    err = mock_esp_ota_set_boot_partition(update_part);
    if (err != ESP_OK) {
        mock_set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Set boot partition failed");
        mock_httpd_resp_set_type(req, "application/json");
        mock_httpd_resp_send(req, "{\"success\":false,\"error\":\"Set boot partition failed\"}", -1);
        return ESP_FAIL;
    }

    mock_set_progress(OTA_STATUS_REBOOTING, 100, firmware_written, firmware_size, NULL);
    mock_httpd_resp_set_type(req, "application/json");
    mock_httpd_resp_send(req, "{\"success\":true,\"message\":\"Rebooting...\"}", -1);
    mock_reboot_called = true;
    return ESP_OK;
}

// --- Test setup/teardown ---

static void reset_mocks(void)
{
    mock_http_status = 0;
    mock_http_error[0] = '\0';
    mock_http_response[0] = '\0';
    mock_http_content_type[0] = '\0';
    mock_ota_begin_fail = false;
    mock_ota_write_fail = false;
    mock_ota_end_fail = false;
    mock_ota_set_boot_fail = false;
    mock_no_partition = false;
    mock_verify_hash_result = true;
    mock_ota_written_len = 0;
    mock_last_status = OTA_STATUS_IDLE;
    mock_last_error[0] = '\0';
    mock_reboot_called = false;
    memset(mock_ota_written, 0, sizeof(mock_ota_written));
}

static void build_valid_image(uint8_t *out, size_t *out_len, uint32_t firmware_size)
{
    ota_image_header_t hdr;
    memset(&hdr, 0, sizeof(hdr));
    hdr.magic = OTA_HEADER_MAGIC;
    hdr.version = 0x00020000;
    hdr.image_size = firmware_size;
    memset(hdr.sha256, 0xBB, OTA_HASH_SIZE);
    memset(hdr.signature, 0xCC, OTA_SIGNATURE_SIZE);

    memcpy(out, &hdr, sizeof(hdr));
    memset(out + sizeof(hdr), 0xDE, firmware_size);
    *out_len = sizeof(hdr) + firmware_size;
}

// --- Tests ---

void test_upload_rejects_zero_content_length(void)
{
    reset_mocks();
    mock_httpd_req_t req = {.content_len = 0, .body = NULL, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_400_BAD_REQUEST, mock_http_status);
    TEST_ASSERT_EQUAL_STRING("Invalid size", mock_http_error);
}

void test_upload_rejects_oversized_content(void)
{
    reset_mocks();
    mock_httpd_req_t req = {.content_len = OTA_MAX_IMAGE_SIZE + 1, .body = NULL, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_400_BAD_REQUEST, mock_http_status);
}

void test_upload_rejects_short_header(void)
{
    reset_mocks();
    uint8_t partial[8] = {0};
    mock_httpd_req_t req = {.content_len = sizeof(partial), .body = partial, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_400_BAD_REQUEST, mock_http_status);
    TEST_ASSERT_EQUAL_STRING("Failed to read header", mock_http_error);
}

void test_upload_rejects_invalid_magic(void)
{
    reset_mocks();
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 256);
    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->magic = 0xDEADBEEF;

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_400_BAD_REQUEST, mock_http_status);
    TEST_ASSERT_EQUAL_STRING("Invalid image magic", mock_http_error);
}

void test_upload_rejects_zero_firmware_size(void)
{
    reset_mocks();
    uint8_t image[256];
    size_t len;
    build_valid_image(image, &len, 64);
    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->image_size = 0;

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL_STRING("Invalid firmware size in header", mock_http_error);
}

void test_upload_rejects_firmware_size_too_large(void)
{
    reset_mocks();
    uint8_t image[256];
    size_t len;
    build_valid_image(image, &len, 64);
    ota_image_header_t *hdr = (ota_image_header_t *)image;
    hdr->image_size = OTA_MAX_IMAGE_SIZE + 1;

    mock_httpd_req_t req = {.content_len = sizeof(ota_image_header_t) + 64, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL_STRING("Invalid firmware size in header", mock_http_error);
}

void test_upload_rejects_no_ota_partition(void)
{
    reset_mocks();
    mock_no_partition = true;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_500_INTERNAL_SERVER_ERROR, mock_http_status);
    TEST_ASSERT_EQUAL_STRING("No OTA partition", mock_http_error);
}

void test_upload_rejects_ota_begin_failure(void)
{
    reset_mocks();
    mock_ota_begin_fail = true;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(HTTPD_500_INTERNAL_SERVER_ERROR, mock_http_status);
    TEST_ASSERT_EQUAL_STRING("OTA begin failed", mock_http_error);
}

void test_upload_incomplete_body(void)
{
    reset_mocks();
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 256);
    size_t truncated = sizeof(ota_image_header_t) + 64;

    mock_httpd_req_t req = {.content_len = truncated, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_FAILED, mock_last_status);
    TEST_ASSERT_EQUAL_STRING("Upload incomplete", mock_last_error);
}

void test_upload_write_failure_aborts(void)
{
    reset_mocks();
    mock_ota_write_fail = true;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_FAILED, mock_last_status);
    TEST_ASSERT_EQUAL_STRING("Upload incomplete", mock_last_error);
}

void test_upload_signature_verification_failure(void)
{
    reset_mocks();
    mock_verify_hash_result = false;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_FAILED, mock_last_status);
    TEST_ASSERT_EQUAL_STRING("Signature verification failed", mock_last_error);
    TEST_ASSERT_TRUE(strstr(mock_http_response, "Signature verification failed") != NULL);
}

void test_upload_ota_end_failure(void)
{
    reset_mocks();
    mock_ota_end_fail = true;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_FAILED, mock_last_status);
    TEST_ASSERT_EQUAL_STRING("OTA end failed", mock_last_error);
}

void test_upload_set_boot_partition_failure(void)
{
    reset_mocks();
    mock_ota_set_boot_fail = true;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_FAILED, mock_last_status);
    TEST_ASSERT_EQUAL_STRING("Set boot partition failed", mock_last_error);
}

void test_upload_success_triggers_reboot(void)
{
    reset_mocks();
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, 128);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_EQUAL(OTA_STATUS_REBOOTING, mock_last_status);
    TEST_ASSERT_TRUE(mock_reboot_called);
    TEST_ASSERT_TRUE(strstr(mock_http_response, "\"success\":true") != NULL);
}

void test_upload_writes_correct_firmware_data(void)
{
    reset_mocks();
    uint32_t fw_size = 256;
    uint8_t image[512];
    size_t len;
    build_valid_image(image, &len, fw_size);

    mock_httpd_req_t req = {.content_len = len, .body = image, .body_pos = 0};
    esp_err_t ret = testable_handler_ota_upload(&req);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_EQUAL(fw_size, mock_ota_written_len);

    uint8_t expected[256];
    memset(expected, 0xDE, 256);
    TEST_ASSERT_TRUE(memcmp(expected, mock_ota_written, fw_size) == 0);
}
