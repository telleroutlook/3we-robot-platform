// SPDX-License-Identifier: Apache-2.0
#include "dtls_transport.h"
#include "motor_control.h"
#include "safety.h"
#include "robot_params.h"

#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "mbedtls/ssl.h"
#include "mbedtls/net_sockets.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/timing.h"
#include "mbedtls/ssl_cookie.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "dtls";

static mbedtls_ssl_context ssl;
static mbedtls_ssl_config conf;
static mbedtls_entropy_context entropy;
static mbedtls_ctr_drbg_context ctr_drbg;
static mbedtls_ssl_cookie_ctx cookie_ctx;
static mbedtls_timing_delay_context timer;
static mbedtls_net_context listen_fd;
static mbedtls_net_context client_fd;

static dtls_config_t current_config;
static dtls_recv_callback_t recv_callback = NULL;
static bool connected = false;
static bool running = false;

static int dtls_psk_callback(void *parameter, mbedtls_ssl_context *ssl_ctx,
                             const unsigned char *identity, size_t identity_len)
{
    (void)parameter;

    if (identity_len != strlen(current_config.psk_identity) ||
        memcmp(identity, current_config.psk_identity, identity_len) != 0) {
        ESP_LOGW(TAG, "Unknown PSK identity");
        return -1;
    }

    return mbedtls_ssl_set_hs_psk(ssl_ctx, current_config.psk_key,
                                   current_config.psk_key_len);
}

esp_err_t dtls_init(const dtls_config_t *config)
{
    if (!config) return ESP_ERR_INVALID_ARG;
    if (config->psk_key_len < 16) {
        ESP_LOGE(TAG, "PSK key too short: %u bytes (minimum 16)", config->psk_key_len);
        return ESP_ERR_INVALID_ARG;
    }
    memcpy(&current_config, config, sizeof(dtls_config_t));

    mbedtls_ssl_init(&ssl);
    mbedtls_ssl_config_init(&conf);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    mbedtls_ssl_cookie_init(&cookie_ctx);
    mbedtls_net_init(&listen_fd);
    mbedtls_net_init(&client_fd);

    // Seed RNG
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                     (const unsigned char *)"robot-platform", 14);
    if (ret != 0) {
        ESP_LOGE(TAG, "DRBG seed failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    // Configure as DTLS 1.2 server (ESP-IDF mbedtls supports DTLS 1.2;
    // DTLS 1.3 will be available when mbedtls adds full support)
    // SECURITY: Enforce DTLS 1.2 minimum to prevent downgrade attacks
    ret = mbedtls_ssl_config_defaults(&conf,
                                       MBEDTLS_SSL_IS_SERVER,
                                       MBEDTLS_SSL_TRANSPORT_DATAGRAM,
                                       MBEDTLS_SSL_PRESET_DEFAULT);
    if (ret != 0) {
        ESP_LOGE(TAG, "SSL config defaults failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    mbedtls_ssl_conf_min_tls_version(&conf, MBEDTLS_SSL_VERSION_TLS1_2);

    mbedtls_ssl_conf_rng(&conf, mbedtls_ctr_drbg_random, &ctr_drbg);
    mbedtls_ssl_conf_psk_cb(&conf, dtls_psk_callback, NULL);

    // DTLS-specific: cookie for DoS protection
    ret = mbedtls_ssl_cookie_setup(&cookie_ctx, mbedtls_ctr_drbg_random, &ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "Cookie setup failed: -0x%04x", -ret);
        return ESP_FAIL;
    }
    mbedtls_ssl_conf_dtls_cookies(&conf,
                                   mbedtls_ssl_cookie_write,
                                   mbedtls_ssl_cookie_check,
                                   &cookie_ctx);

    // Timeouts
    mbedtls_ssl_conf_handshake_timeout(&conf, 1000, config->handshake_timeout_ms);
    mbedtls_ssl_conf_read_timeout(&conf, config->session_timeout_ms);

    // Prefer AEAD ciphersuites for safety-critical control channel
    static const int ciphersuites[] = {
        MBEDTLS_TLS_PSK_WITH_AES_128_GCM_SHA256,
        MBEDTLS_TLS_PSK_WITH_AES_256_GCM_SHA384,
        MBEDTLS_TLS_PSK_WITH_AES_128_CCM,
        MBEDTLS_TLS_ECDHE_PSK_WITH_AES_128_CBC_SHA256,
        0
    };
    mbedtls_ssl_conf_ciphersuites(&conf, ciphersuites);

    ret = mbedtls_ssl_setup(&ssl, &conf);
    if (ret != 0) {
        ESP_LOGE(TAG, "SSL setup failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    mbedtls_ssl_set_timer_cb(&ssl, &timer,
                              mbedtls_timing_set_delay,
                              mbedtls_timing_get_delay);

    ESP_LOGI(TAG, "DTLS initialized (port %d, PSK mode)", config->listen_port);
    return ESP_OK;
}

esp_err_t dtls_start(void)
{
    char port_str[6];
    snprintf(port_str, sizeof(port_str), "%d", current_config.listen_port);

    int ret = mbedtls_net_bind(&listen_fd, NULL, port_str, MBEDTLS_NET_PROTO_UDP);
    if (ret != 0) {
        ESP_LOGE(TAG, "Bind failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    running = true;
    ESP_LOGI(TAG, "DTLS server listening on UDP port %s", port_str);
    return ESP_OK;
}

void dtls_stop(void)
{
    running = false;
    mbedtls_net_free(&client_fd);
    mbedtls_net_free(&listen_fd);
    mbedtls_ssl_free(&ssl);
    mbedtls_ssl_config_free(&conf);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    mbedtls_ssl_cookie_free(&cookie_ctx);
    connected = false;
}

esp_err_t dtls_send(const uint8_t *data, size_t len)
{
    if (!connected) return ESP_ERR_INVALID_STATE;

    int ret = mbedtls_ssl_write(&ssl, data, len);
    if (ret < 0) {
        ESP_LOGW(TAG, "Send failed: -0x%04x", -ret);
        return ESP_FAIL;
    }
    return ESP_OK;
}

void dtls_set_recv_callback(dtls_recv_callback_t cb)
{
    recv_callback = cb;
}

bool dtls_is_connected(void)
{
    return connected;
}

void dtls_task(void *params)
{
    uint8_t buf[256];

    while (running) {
        // Wait for client connection
        mbedtls_ssl_session_reset(&ssl);
        mbedtls_net_free(&client_fd);

        ESP_LOGI(TAG, "Waiting for DTLS client...");

        // Accept (UDP: just receive first datagram)
        unsigned char client_ip[16] = {0};
        size_t cliip_len = 0;
        int ret = mbedtls_net_accept(&listen_fd, &client_fd, client_ip, sizeof(client_ip), &cliip_len);
        if (ret != 0) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        mbedtls_ssl_set_bio(&ssl, &client_fd,
                            mbedtls_net_send, mbedtls_net_recv, mbedtls_net_recv_timeout);

        // DTLS handshake
        do {
            ret = mbedtls_ssl_handshake(&ssl);
        } while (ret == MBEDTLS_ERR_SSL_WANT_READ || ret == MBEDTLS_ERR_SSL_WANT_WRITE);

        if (ret != 0) {
            ESP_LOGW(TAG, "Handshake failed: -0x%04x", -ret);
            continue;
        }

        connected = true;
        ESP_LOGI(TAG, "DTLS client connected (cipher: %s)",
                 mbedtls_ssl_get_ciphersuite(&ssl));

        // Read loop
        while (connected && running) {
            ret = mbedtls_ssl_read(&ssl, buf, sizeof(buf));

            if (ret == MBEDTLS_ERR_SSL_WANT_READ) {
                vTaskDelay(pdMS_TO_TICKS(1));
                continue;
            }

            if (ret == MBEDTLS_ERR_SSL_TIMEOUT) {
                ESP_LOGW(TAG, "Session timeout - disconnecting");
                break;
            }

            if (ret == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY || ret <= 0) {
                ESP_LOGI(TAG, "Client disconnected");
                break;
            }

            if (recv_callback) {
                recv_callback(buf, (size_t)ret, (const char *)client_ip, 0);
            }
        }

        connected = false;
        mbedtls_ssl_close_notify(&ssl);
    }

    vTaskDelete(NULL);
}
