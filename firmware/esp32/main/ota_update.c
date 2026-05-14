// SPDX-License-Identifier: Apache-2.0
#include "ota_update.h"
#include "ota_signing.h"
#include "ota_preflight.h"
#include "ota_compat.h"

#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_http_client.h"
#include "esp_http_server.h"
#include "esp_partition.h"
#include "esp_tls.h"
#include "esp_crt_bundle.h"
#include "esp_timer.h"
#include "mbedtls/sha256.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include <string.h>
#include <stdio.h>

static const char *TAG = "ota_update";

#define OTA_BUF_SIZE        4096
#define OTA_MAX_URL_LEN     256
#define OTA_MAX_IMAGE_SIZE  (4 * 1024 * 1024)
#define OTA_RATE_LIMIT_BASE_S  60
#define OTA_RATE_LIMIT_MAX_S   300

static ota_progress_t s_progress = {0};
static SemaphoreHandle_t s_mutex = NULL;
static char s_pending_url[OTA_MAX_URL_LEN] = {0};
static bool s_update_requested = false;
static httpd_handle_t s_httpd = NULL;
static int64_t s_last_upload_us = 0;
static uint8_t s_upload_fail_streak = 0;

static void set_progress(ota_status_t status, uint8_t pct,
                         uint32_t received, uint32_t total, const char *err)
{
    if (s_mutex) xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_progress.status = status;
    s_progress.progress_pct = pct;
    s_progress.bytes_received = received;
    s_progress.bytes_total = total;
    if (err) {
        strncpy(s_progress.error_msg, err, sizeof(s_progress.error_msg) - 1); // nosemgrep
    } else {
        s_progress.error_msg[0] = '\0';
    }
    if (s_mutex) xSemaphoreGive(s_mutex);
}

static esp_err_t perform_ota_from_url(const char *url)
{
    // Pre-flight safety gate
    ota_preflight_result_t preflight = ota_preflight_check();
    if (!preflight.overall_pass) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, preflight.fail_reason);
        return ESP_ERR_INVALID_STATE;
    }

    set_progress(OTA_STATUS_DOWNLOADING, 0, 0, 0, NULL);

    esp_http_client_config_t http_cfg = {
        .url = url,
        .timeout_ms = 30000,
        .crt_bundle_attach = esp_crt_bundle_attach,
    };
    esp_http_client_handle_t client = esp_http_client_init(&http_cfg);
    if (!client) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "HTTP client init failed");
        return ESP_FAIL;
    }

    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "HTTP open failed: %s", esp_err_to_name(err));
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "HTTP connection failed");
        esp_http_client_cleanup(client);
        return err;
    }

    int content_length = esp_http_client_fetch_headers(client);
    if (content_length <= 0) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Invalid content length");
        esp_http_client_cleanup(client);
        return ESP_ERR_INVALID_SIZE;
    }
    if ((size_t)content_length > OTA_MAX_IMAGE_SIZE) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Image too large");
        esp_http_client_cleanup(client);
        return ESP_ERR_INVALID_SIZE;
    }

    const esp_partition_t *update_part = esp_ota_get_next_update_partition(NULL);
    if (!update_part) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "No OTA partition");
        esp_http_client_cleanup(client);
        return ESP_ERR_NOT_FOUND;
    }

    // Read header first
    uint8_t header_buf[sizeof(ota_image_header_t)];
    int header_read = esp_http_client_read(client, (char *)header_buf, sizeof(header_buf));
    if (header_read != (int)sizeof(ota_image_header_t)) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Failed to read OTA header");
        esp_http_client_cleanup(client);
        return ESP_ERR_INVALID_SIZE;
    }

    const ota_image_header_t *header = (const ota_image_header_t *)header_buf;
    if (header->magic != OTA_HEADER_MAGIC) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Invalid image magic");
        esp_http_client_cleanup(client);
        return ESP_ERR_INVALID_STATE;
    }

    // Check version before downloading entire image
    esp_err_t ver_err = ota_check_version_policy(header->version);
    if (ver_err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Version rollback rejected");
        esp_http_client_cleanup(client);
        return ver_err;
    }

    // Check protocol compatibility
    if (!ota_check_compatibility(header->version)) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Protocol version incompatible");
        esp_http_client_cleanup(client);
        return ESP_ERR_INVALID_VERSION;
    }

    uint32_t firmware_size = header->image_size;
    uint32_t total = (uint32_t)content_length;
    uint32_t received = (uint32_t)header_read;

    // Begin OTA write for firmware portion
    esp_ota_handle_t ota_handle;
    err = esp_ota_begin(update_part, firmware_size, &ota_handle);
    if (err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "OTA begin failed");
        esp_http_client_cleanup(client);
        return err;
    }

    set_progress(OTA_STATUS_DOWNLOADING, (uint8_t)((received * 100) / total),
                 received, total, NULL);

    // Stream firmware to OTA partition while computing SHA-256
    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);

    uint8_t *buf = malloc(OTA_BUF_SIZE);
    if (!buf) {
        mbedtls_sha256_free(&sha_ctx);
        esp_ota_abort(ota_handle);
        esp_http_client_cleanup(client);
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Out of memory");
        return ESP_ERR_NO_MEM;
    }

    uint32_t firmware_written = 0;
    bool download_ok = true;
    uint8_t last_pct = 0;

    while (firmware_written < firmware_size) {
        int to_read = (int)((firmware_size - firmware_written) < OTA_BUF_SIZE ?
                            (firmware_size - firmware_written) : OTA_BUF_SIZE);
        int read_len = esp_http_client_read(client, (char *)buf, to_read);
        if (read_len <= 0) {
            download_ok = false;
            break;
        }

        mbedtls_sha256_update(&sha_ctx, buf, (size_t)read_len);

        err = esp_ota_write(ota_handle, buf, (size_t)read_len);
        if (err != ESP_OK) {
            download_ok = false;
            break;
        }

        firmware_written += (uint32_t)read_len;
        received += (uint32_t)read_len;
        uint8_t pct = (uint8_t)((received * 100) / total);
        if (pct != last_pct) {
            set_progress(OTA_STATUS_DOWNLOADING, pct, received, total, NULL);
            last_pct = pct;
        }
    }

    free(buf);
    esp_http_client_cleanup(client);

    if (!download_ok || firmware_written != firmware_size) {
        mbedtls_sha256_free(&sha_ctx);
        esp_ota_abort(ota_handle);
        set_progress(OTA_STATUS_FAILED, 0, received, total, "Download incomplete");
        return ESP_ERR_INVALID_SIZE;
    }

    // Finalize streaming hash and verify signature without re-reading flash
    set_progress(OTA_STATUS_VERIFYING, 100, received, total, NULL);

    uint8_t computed_hash[OTA_HASH_SIZE];
    mbedtls_sha256_finish(&sha_ctx, computed_hash);
    mbedtls_sha256_free(&sha_ctx);

    if (!ota_verify_image_hash(computed_hash, firmware_size, header)) {
        esp_ota_abort(ota_handle);
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Signature verification failed");
        return ESP_ERR_OTA_VALIDATE_FAILED;
    }

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "OTA end failed");
        return err;
    }

    // Re-read flash to verify written content matches the signed hash
    uint8_t flash_hash[OTA_HASH_SIZE];
    mbedtls_sha256_context verify_ctx;
    mbedtls_sha256_init(&verify_ctx);
    mbedtls_sha256_starts(&verify_ctx, 0);

    uint8_t *vbuf = malloc(OTA_BUF_SIZE);
    if (!vbuf) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Out of memory for flash verify");
        return ESP_ERR_NO_MEM;
    }

    uint32_t offset = 0;
    while (offset < firmware_size) {
        uint32_t to_read = (firmware_size - offset) < OTA_BUF_SIZE ?
                           (firmware_size - offset) : OTA_BUF_SIZE;
        err = esp_partition_read(update_part, offset, vbuf, to_read);
        if (err != ESP_OK) {
            free(vbuf);
            mbedtls_sha256_free(&verify_ctx);
            set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Flash read-back failed");
            return err;
        }
        mbedtls_sha256_update(&verify_ctx, vbuf, to_read);
        offset += to_read;
    }
    free(vbuf);

    mbedtls_sha256_finish(&verify_ctx, flash_hash);
    mbedtls_sha256_free(&verify_ctx);

    if (memcmp(computed_hash, flash_hash, OTA_HASH_SIZE) != 0) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Flash content mismatch after write");
        return ESP_ERR_OTA_VALIDATE_FAILED;
    }

    // Set boot partition
    set_progress(OTA_STATUS_APPLYING, 100, received, total, NULL);
    err = esp_ota_set_boot_partition(update_part);
    if (err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Set boot partition failed");
        return err;
    }

    set_progress(OTA_STATUS_REBOOTING, 100, received, total, NULL);
    ESP_LOGI(TAG, "OTA complete, rebooting in 2s...");
    vTaskDelay(pdMS_TO_TICKS(2000));
    esp_restart();

    return ESP_OK; // unreachable
}

static esp_err_t handler_ota_upload(httpd_req_t *req)
{
    // Require OTA token in Authorization header for local upload security
    char auth_hdr[128] = {0};
    esp_err_t hdr_err = httpd_req_get_hdr_value_str(req, "Authorization", auth_hdr, sizeof(auth_hdr));
    if (hdr_err != ESP_OK || !ota_signing_check_upload_token(auth_hdr)) {
        httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Unauthorized");
        return ESP_FAIL;
    }

    // Rate limiting: exponential backoff to protect flash from abuse
    int64_t now_us = esp_timer_get_time();
    uint32_t cooldown_s = OTA_RATE_LIMIT_BASE_S << (s_upload_fail_streak < 3 ? s_upload_fail_streak : 2);
    if (cooldown_s > OTA_RATE_LIMIT_MAX_S) cooldown_s = OTA_RATE_LIMIT_MAX_S;
    if (s_last_upload_us != 0 && (now_us - s_last_upload_us) < (int64_t)cooldown_s * 1000000LL) {
        ESP_LOGW(TAG, "OTA upload rate-limited (cooldown %lus)", (unsigned long)cooldown_s);
        httpd_resp_set_status(req, "429 Too Many Requests");
        httpd_resp_send(req, "Rate limited, try again later", HTTPD_RESP_USE_STRLEN);
        return ESP_FAIL;
    }
    s_last_upload_us = now_us;

    if (req->content_len == 0 || req->content_len > OTA_MAX_IMAGE_SIZE) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid size");
        return ESP_FAIL;
    }

    // Pre-flight safety gate
    ota_preflight_result_t preflight = ota_preflight_check();
    if (!preflight.overall_pass) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, preflight.fail_reason);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, preflight.fail_reason);
        return ESP_FAIL;
    }

    uint8_t *buf = malloc(OTA_BUF_SIZE);
    if (!buf) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Out of memory");
        return ESP_FAIL;
    }

    // Read header first
    int ret = httpd_req_recv(req, (char *)buf, sizeof(ota_image_header_t));
    if (ret != (int)sizeof(ota_image_header_t)) {
        free(buf);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Failed to read header");
        return ESP_FAIL;
    }

    ota_image_header_t header;
    memcpy(&header, buf, sizeof(header));

    if (header.magic != OTA_HEADER_MAGIC) {
        free(buf);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid image magic");
        return ESP_FAIL;
    }

    uint32_t firmware_size = header.image_size;
    if (firmware_size == 0 || firmware_size > OTA_MAX_IMAGE_SIZE) {
        free(buf);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid firmware size in header");
        return ESP_FAIL;
    }

    // Reject version rollback (consistent with perform_ota_from_url)
    esp_err_t ver_err = ota_check_version_policy(header.version);
    if (ver_err != ESP_OK) {
        free(buf);
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Version rollback rejected");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Version rollback rejected");
        return ESP_FAIL;
    }

    // Check protocol compatibility
    if (!ota_check_compatibility(header.version)) {
        free(buf);
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Protocol version incompatible");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Protocol version incompatible");
        return ESP_FAIL;
    }

    const esp_partition_t *update_part = esp_ota_get_next_update_partition(NULL);
    if (!update_part) {
        free(buf);
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "No OTA partition");
        return ESP_FAIL;
    }

    esp_ota_handle_t ota_handle;
    esp_err_t err = esp_ota_begin(update_part, firmware_size, &ota_handle);
    if (err != ESP_OK) {
        free(buf);
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "OTA begin failed");
        return ESP_FAIL;
    }

    set_progress(OTA_STATUS_DOWNLOADING, 0, 0, firmware_size, NULL);

    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);

    uint32_t firmware_written = 0;
    bool upload_ok = true;

    while (firmware_written < firmware_size) {
        int to_read = (int)((firmware_size - firmware_written) < OTA_BUF_SIZE ?
                            (firmware_size - firmware_written) : OTA_BUF_SIZE);
        ret = httpd_req_recv(req, (char *)buf, to_read);
        if (ret <= 0) {
            upload_ok = false;
            break;
        }

        mbedtls_sha256_update(&sha_ctx, buf, (size_t)ret);

        err = esp_ota_write(ota_handle, buf, (size_t)ret);
        if (err != ESP_OK) {
            upload_ok = false;
            break;
        }

        firmware_written += (uint32_t)ret;
        uint8_t pct = (uint8_t)((firmware_written * 100) / firmware_size);
        set_progress(OTA_STATUS_DOWNLOADING, pct, firmware_written, firmware_size, NULL);
    }

    free(buf);

    if (!upload_ok || firmware_written != firmware_size) {
        mbedtls_sha256_free(&sha_ctx);
        esp_ota_abort(ota_handle);
        s_upload_fail_streak++;
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Upload incomplete");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Upload incomplete");
        return ESP_FAIL;
    }

    set_progress(OTA_STATUS_VERIFYING, 100, firmware_written, firmware_size, NULL);

    uint8_t computed_hash[OTA_HASH_SIZE];
    mbedtls_sha256_finish(&sha_ctx, computed_hash);
    mbedtls_sha256_free(&sha_ctx);

    if (!ota_verify_image_hash(computed_hash, firmware_size, &header)) {
        esp_ota_abort(ota_handle);
        s_upload_fail_streak++;
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Signature verification failed");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_send(req, "{\"success\":false,\"error\":\"Signature verification failed\"}", -1);
        return ESP_FAIL;
    }

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "OTA end failed");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_send(req, "{\"success\":false,\"error\":\"OTA finalize failed\"}", -1);
        return ESP_FAIL;
    }

    err = esp_ota_set_boot_partition(update_part);
    if (err != ESP_OK) {
        set_progress(OTA_STATUS_FAILED, 0, 0, 0, "Set boot partition failed");
        httpd_resp_set_type(req, "application/json");
        httpd_resp_send(req, "{\"success\":false,\"error\":\"Set boot partition failed\"}", -1);
        return ESP_FAIL;
    }

    set_progress(OTA_STATUS_REBOOTING, 100, firmware_written, firmware_size, NULL);
    s_upload_fail_streak = 0;
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, "{\"success\":true,\"message\":\"Rebooting...\"}", -1);

    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    return ESP_OK;
}

static esp_err_t handler_ota_status(httpd_req_t *req)
{
    ota_progress_t p = ota_update_get_progress();
    char escaped_error[256] = {0};
    size_t j = 0;
    for (size_t i = 0; p.error_msg[i] != '\0' && j < sizeof(escaped_error) - 2; i++) {
        char c = p.error_msg[i];
        if (c == '"' || c == '\\') {
            escaped_error[j++] = '\\';
        }
        if (j < sizeof(escaped_error) - 1) {
            escaped_error[j++] = c;
        }
    }
    escaped_error[j] = '\0';
    char resp[512];
    snprintf(resp, sizeof(resp),
             "{\"status\":%d,\"progress\":%d,\"received\":%lu,\"total\":%lu,"
             "\"version\":\"0x%08lX\",\"error\":\"%s\"}",
             (int)p.status, (int)p.progress_pct,
             (unsigned long)p.bytes_received, (unsigned long)p.bytes_total,
             (unsigned long)ota_get_current_version(),
             escaped_error);
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, resp, -1);
}

esp_err_t ota_update_init(httpd_handle_t httpd)
{
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) return ESP_ERR_NO_MEM;

    s_httpd = httpd;

    if (s_httpd) {
        const httpd_uri_t uri_upload = {
            .uri = "/ota/upload", .method = HTTP_POST, .handler = handler_ota_upload
        };
        const httpd_uri_t uri_status = {
            .uri = "/ota/status", .method = HTTP_GET, .handler = handler_ota_status
        };
        httpd_register_uri_handler(s_httpd, &uri_upload);
        httpd_register_uri_handler(s_httpd, &uri_status);
    }

    set_progress(OTA_STATUS_IDLE, 0, 0, 0, NULL);
    ESP_LOGI(TAG, "OTA update module initialized (version 0x%08lX)",
             (unsigned long)ota_get_current_version());
    return ESP_OK;
}

esp_err_t ota_update_start_from_url(const char *url)
{
    if (!url || strlen(url) == 0) return ESP_ERR_INVALID_ARG;

    if (s_mutex) xSemaphoreTake(s_mutex, portMAX_DELAY);
    if (s_progress.status == OTA_STATUS_DOWNLOADING ||
        s_progress.status == OTA_STATUS_APPLYING) {
        if (s_mutex) xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    strncpy(s_pending_url, url, OTA_MAX_URL_LEN - 1); // nosemgrep
    s_pending_url[OTA_MAX_URL_LEN - 1] = '\0';
    s_update_requested = true;
    if (s_mutex) xSemaphoreGive(s_mutex);
    return ESP_OK;
}

ota_progress_t ota_update_get_progress(void)
{
    ota_progress_t copy;
    if (s_mutex) xSemaphoreTake(s_mutex, portMAX_DELAY);
    memcpy(&copy, &s_progress, sizeof(copy));
    if (s_mutex) xSemaphoreGive(s_mutex);
    return copy;
}

void ota_update_task(void *params)
{
    (void)params;

    while (1) {
        bool should_update = false;
        char url_copy[OTA_MAX_URL_LEN] = {0};

        if (s_mutex) xSemaphoreTake(s_mutex, portMAX_DELAY);
        if (s_update_requested) {
            s_update_requested = false;
            memcpy(url_copy, s_pending_url, OTA_MAX_URL_LEN);
            should_update = true;
        }
        if (s_mutex) xSemaphoreGive(s_mutex);

        if (should_update) {
            perform_ota_from_url(url_copy);
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
