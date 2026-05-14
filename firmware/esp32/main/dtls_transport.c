// SPDX-License-Identifier: Apache-2.0
#include "dtls_transport.h"
#include "dtls_authority.h"
#include "motor_control.h"
#include "safety.h"
#include "robot_params.h"

#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "mbedtls/ssl.h"
#include "mbedtls/net_sockets.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/timing.h"
#include "mbedtls/ssl_cookie.h"
#include "mbedtls/ssl_cache.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_mac.h"

#include <string.h>

static const char *TAG = "dtls";

typedef struct {
    mbedtls_ssl_context       ssl;
    mbedtls_net_context       client_fd;
    mbedtls_timing_delay_context timer;
    dtls_session_state_t      state;
    dtls_role_t               role;
    uint8_t                   priority;
    char                      identity[32];
    char                      peer_ip[16];
    int64_t                   last_recv_us;
    bool                      session_resumed;
} dtls_session_internal_t;

static SemaphoreHandle_t ssl_mutex = NULL;

static mbedtls_ssl_config conf;
static mbedtls_entropy_context entropy;
static mbedtls_ctr_drbg_context ctr_drbg;
static mbedtls_ssl_cookie_ctx cookie_ctx;
static mbedtls_ssl_cache_context cache_ctx;
static mbedtls_net_context listen_fd;

static dtls_session_internal_t sessions[DTLS_MAX_SESSIONS];
static dtls_authority_t authority;
static dtls_operator_entry_t operator_table[DTLS_MAX_OPERATORS];
static uint8_t operator_count = 0;

static dtls_config_t current_config;
static dtls_recv_callback_t recv_callback = NULL;
static bool running = false;
static uint8_t max_sessions = DTLS_MAX_SESSIONS;

static int find_session_by_ssl(const mbedtls_ssl_context *ssl_ctx)
{
    for (int i = 0; i < max_sessions; i++) {
        if (&sessions[i].ssl == ssl_ctx) {
            return i;
        }
    }
    return -1;
}

static int find_empty_slot(void)
{
    for (int i = 0; i < max_sessions; i++) {
        if (sessions[i].state == DTLS_SESSION_EMPTY) {
            return i;
        }
    }
    return -1;
}

static void cleanup_session(int idx)
{
    if (idx < 0 || idx >= max_sessions) return;

    authority_session_disconnected(&authority, (uint8_t)idx);

    if (sessions[idx].state >= DTLS_SESSION_HANDSHAKING) {
        mbedtls_ssl_close_notify(&sessions[idx].ssl);
        mbedtls_ssl_free(&sessions[idx].ssl);
        mbedtls_net_free(&sessions[idx].client_fd);
    }

    memset(&sessions[idx], 0, sizeof(dtls_session_internal_t));
    sessions[idx].state = DTLS_SESSION_EMPTY;
    sessions[idx].client_fd.fd = -1;
}

static int dtls_psk_callback(void *parameter, mbedtls_ssl_context *ssl_ctx,
                             const unsigned char *identity_data, size_t identity_len)
{
    (void)parameter;

    for (int i = 0; i < operator_count; i++) {
        size_t op_id_len = strlen(operator_table[i].identity);
        if (op_id_len == identity_len &&
            memcmp(operator_table[i].identity, identity_data, identity_len) == 0) {

            int session_idx = find_session_by_ssl(ssl_ctx);
            if (session_idx >= 0) {
                sessions[session_idx].priority = operator_table[i].priority;
                sessions[session_idx].role = operator_table[i].role;
                strncpy(sessions[session_idx].identity, operator_table[i].identity, // nosemgrep
                        sizeof(sessions[session_idx].identity) - 1);
                sessions[session_idx].identity[sizeof(sessions[session_idx].identity) - 1] = '\0';
            }

            return mbedtls_ssl_set_hs_psk(ssl_ctx,
                                           operator_table[i].psk_key,
                                           operator_table[i].psk_key_len);
        }
    }

    if (strlen(current_config.psk_identity) == identity_len &&
        memcmp(current_config.psk_identity, identity_data, identity_len) == 0) {

        int session_idx = find_session_by_ssl(ssl_ctx);
        if (session_idx >= 0) {
            sessions[session_idx].priority = 0;
            sessions[session_idx].role = DTLS_ROLE_OPERATOR;
            strncpy(sessions[session_idx].identity, current_config.psk_identity, // nosemgrep
                    sizeof(sessions[session_idx].identity) - 1);
            sessions[session_idx].identity[sizeof(sessions[session_idx].identity) - 1] = '\0';
        }

        return mbedtls_ssl_set_hs_psk(ssl_ctx, current_config.psk_key,
                                       current_config.psk_key_len);
    }

    ESP_LOGW(TAG, "Unknown PSK identity (len=%u)", (unsigned)identity_len);
    return -1;
}

esp_err_t dtls_init(const dtls_config_t *config)
{
    if (!config) return ESP_ERR_INVALID_ARG;
    if (config->psk_key_len < 16 || config->psk_key_len > sizeof(config->psk_key)) {
        ESP_LOGE(TAG, "PSK key length invalid: %u bytes (must be 16-%u)",
                 config->psk_key_len, (unsigned)sizeof(config->psk_key));
        return ESP_ERR_INVALID_ARG;
    }
    memcpy(&current_config, config, sizeof(dtls_config_t));

    if (config->max_sessions > 0 && config->max_sessions <= DTLS_MAX_SESSIONS) {
        max_sessions = config->max_sessions;
    } else {
        max_sessions = DTLS_MAX_SESSIONS;
    }

    if (!ssl_mutex) {
        ssl_mutex = xSemaphoreCreateMutex();
        if (!ssl_mutex) return ESP_ERR_NO_MEM;
    }

    authority_init(&authority);

    for (int i = 0; i < DTLS_MAX_SESSIONS; i++) {
        memset(&sessions[i], 0, sizeof(dtls_session_internal_t));
        sessions[i].state = DTLS_SESSION_EMPTY;
        sessions[i].client_fd.fd = -1;
    }

    mbedtls_ssl_config_init(&conf);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    mbedtls_ssl_cookie_init(&cookie_ctx);
    mbedtls_ssl_cache_init(&cache_ctx);
    mbedtls_net_init(&listen_fd);

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    uint8_t pers[20];
    memcpy(pers, "robot-platform", 14);
    memcpy(pers + 14, mac, 6);
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                     pers, sizeof(pers));
    if (ret != 0) {
        ESP_LOGE(TAG, "DRBG seed failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

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

    ret = mbedtls_ssl_cookie_setup(&cookie_ctx, mbedtls_ctr_drbg_random, &ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "Cookie setup failed: -0x%04x", -ret);
        return ESP_FAIL;
    }
    mbedtls_ssl_conf_dtls_cookies(&conf,
                                   mbedtls_ssl_cookie_write,
                                   mbedtls_ssl_cookie_check,
                                   &cookie_ctx);

    mbedtls_ssl_cache_set_timeout(&cache_ctx, config->session_timeout_ms / 1000);
    mbedtls_ssl_cache_set_max_entries(&cache_ctx, max_sessions * 2);
    mbedtls_ssl_conf_session_cache(&conf, &cache_ctx,
                                    mbedtls_ssl_cache_get,
                                    mbedtls_ssl_cache_set);

    mbedtls_ssl_conf_handshake_timeout(&conf, 1000, config->handshake_timeout_ms);
    mbedtls_ssl_conf_read_timeout(&conf, config->session_timeout_ms);

    static const int ciphersuites[] = {
        MBEDTLS_TLS_PSK_WITH_AES_128_GCM_SHA256,
        MBEDTLS_TLS_PSK_WITH_AES_256_GCM_SHA384,
        MBEDTLS_TLS_PSK_WITH_AES_128_CCM,
        0
    };
    mbedtls_ssl_conf_ciphersuites(&conf, ciphersuites);

    ESP_LOGI(TAG, "DTLS initialized (port %d, max_sessions=%d)",
             config->listen_port, max_sessions);
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

    for (int i = 0; i < max_sessions; i++) {
        cleanup_session(i);
    }

    mbedtls_net_free(&listen_fd);
    mbedtls_ssl_config_free(&conf);
    mbedtls_ssl_cache_free(&cache_ctx);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    mbedtls_ssl_cookie_free(&cookie_ctx);
}

esp_err_t dtls_send(const uint8_t *data, size_t len)
{
    int8_t holder = authority_get_holder(&authority);
    if (holder < 0) return ESP_ERR_INVALID_STATE;
    return dtls_send_to_session((uint8_t)holder, data, len);
}

esp_err_t dtls_send_to_session(uint8_t session_id, const uint8_t *data, size_t len)
{
    if (session_id >= max_sessions) return ESP_ERR_INVALID_ARG;
    if (sessions[session_id].state != DTLS_SESSION_ACTIVE) return ESP_ERR_INVALID_STATE;

    xSemaphoreTake(ssl_mutex, portMAX_DELAY);
    int ret = mbedtls_ssl_write(&sessions[session_id].ssl, data, len);
    xSemaphoreGive(ssl_mutex);

    if (ret < 0) {
        ESP_LOGW(TAG, "Send to session %d failed: -0x%04x", session_id, -ret);
        return ESP_FAIL;
    }
    return ESP_OK;
}

esp_err_t dtls_broadcast(const uint8_t *data, size_t len)
{
    esp_err_t result = ESP_OK;
    xSemaphoreTake(ssl_mutex, portMAX_DELAY);
    for (int i = 0; i < max_sessions; i++) {
        if (sessions[i].state == DTLS_SESSION_ACTIVE) {
            int ret = mbedtls_ssl_write(&sessions[i].ssl, data, len);
            if (ret < 0) {
                ESP_LOGW(TAG, "Broadcast to session %d failed: -0x%04x", i, -ret);
                result = ESP_FAIL;
            }
        }
    }
    xSemaphoreGive(ssl_mutex);
    return result;
}

void dtls_set_recv_callback(dtls_recv_callback_t cb)
{
    recv_callback = cb;
}

bool dtls_is_connected(void)
{
    for (int i = 0; i < max_sessions; i++) {
        if (sessions[i].state == DTLS_SESSION_ACTIVE) return true;
    }
    return false;
}

bool dtls_session_was_resumed(void)
{
    int8_t holder = authority_get_holder(&authority);
    if (holder >= 0) return sessions[holder].session_resumed;
    return false;
}

uint8_t dtls_active_session_count(void)
{
    uint8_t count = 0;
    for (int i = 0; i < max_sessions; i++) {
        if (sessions[i].state == DTLS_SESSION_ACTIVE) count++;
    }
    return count;
}

int8_t dtls_get_authority_holder(void)
{
    return authority_get_holder(&authority);
}

bool dtls_session_has_authority(uint8_t session_id)
{
    return authority_is_holder(&authority, session_id);
}

dtls_session_state_t dtls_get_session_state(uint8_t session_id)
{
    if (session_id >= max_sessions) return DTLS_SESSION_EMPTY;
    return sessions[session_id].state;
}

esp_err_t dtls_register_operator(const dtls_operator_entry_t *op)
{
    if (!op) return ESP_ERR_INVALID_ARG;
    if (op->psk_key_len < 16 || op->psk_key_len > sizeof(op->psk_key)) {
        return ESP_ERR_INVALID_ARG;
    }
    if (operator_count >= DTLS_MAX_OPERATORS) return ESP_ERR_NO_MEM;

    memcpy(&operator_table[operator_count], op, sizeof(dtls_operator_entry_t));
    operator_count++;
    ESP_LOGI(TAG, "Registered operator '%s' (priority=%d, role=%d)",
             op->identity, op->priority, op->role);
    return ESP_OK;
}

esp_err_t dtls_load_operators_from_nvs(void)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open("dtls_ops", NVS_READONLY, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "No saved operators in NVS");
        return ESP_OK;
    }
    if (err != ESP_OK) return err;

    uint8_t count = 0;
    err = nvs_get_u8(handle, "count", &count);
    if (err != ESP_OK || count == 0) {
        nvs_close(handle);
        return ESP_OK;
    }

    for (uint8_t i = 0; i < count && i < DTLS_MAX_OPERATORS; i++) {
        char key[12];
        snprintf(key, sizeof(key), "op_%d", i);

        dtls_operator_entry_t op;
        size_t len = sizeof(dtls_operator_entry_t);
        err = nvs_get_blob(handle, key, &op, &len);
        if (err != ESP_OK || len != sizeof(dtls_operator_entry_t)) {
            ESP_LOGW(TAG, "Failed to load operator %d from NVS", i);
            continue;
        }
        dtls_register_operator(&op);
    }

    nvs_close(handle);
    ESP_LOGI(TAG, "Loaded %d operators from NVS", operator_count);
    return ESP_OK;
}

esp_err_t dtls_save_operator_to_nvs(const dtls_operator_entry_t *op)
{
    if (!op) return ESP_ERR_INVALID_ARG;

    nvs_handle_t handle;
    esp_err_t err = nvs_open("dtls_ops", NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;

    uint8_t count = 0;
    nvs_get_u8(handle, "count", &count);

    if (count >= DTLS_MAX_OPERATORS) {
        nvs_close(handle);
        return ESP_ERR_NO_MEM;
    }

    char key[12];
    snprintf(key, sizeof(key), "op_%d", count);
    err = nvs_set_blob(handle, key, op, sizeof(dtls_operator_entry_t));
    if (err != ESP_OK) { nvs_close(handle); return err; }

    count++;
    err = nvs_set_u8(handle, "count", count);
    if (err != ESP_OK) { nvs_close(handle); return err; }

    err = nvs_commit(handle);
    nvs_close(handle);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Saved operator '%s' to NVS (slot %d)", op->identity, count - 1);
    }
    return err;
}

static void handle_new_connection(void)
{
    int slot = find_empty_slot();
    if (slot < 0) {
        ESP_LOGW(TAG, "All session slots full, rejecting connection");
        mbedtls_net_context tmp_fd;
        mbedtls_net_init(&tmp_fd);
        unsigned char tmp_ip[16] = {0};
        size_t tmp_len = 0;
        mbedtls_net_accept(&listen_fd, &tmp_fd, tmp_ip, sizeof(tmp_ip), &tmp_len);
        mbedtls_net_free(&tmp_fd);
        return;
    }

    unsigned char client_ip[16] = {0};
    size_t cliip_len = 0;
    mbedtls_net_init(&sessions[slot].client_fd);
    int ret = mbedtls_net_accept(&listen_fd, &sessions[slot].client_fd,
                                  client_ip, sizeof(client_ip), &cliip_len);
    if (ret != 0) {
        ESP_LOGW(TAG, "Accept failed: -0x%04x", -ret);
        mbedtls_net_free(&sessions[slot].client_fd);
        return;
    }

    memcpy(sessions[slot].peer_ip, client_ip,
           cliip_len < sizeof(sessions[slot].peer_ip) ? cliip_len : sizeof(sessions[slot].peer_ip));

    mbedtls_ssl_init(&sessions[slot].ssl);
    ret = mbedtls_ssl_setup(&sessions[slot].ssl, &conf);
    if (ret != 0) {
        ESP_LOGE(TAG, "SSL setup for slot %d failed: -0x%04x", slot, -ret);
        mbedtls_ssl_free(&sessions[slot].ssl);
        mbedtls_net_free(&sessions[slot].client_fd);
        return;
    }

    mbedtls_ssl_set_timer_cb(&sessions[slot].ssl, &sessions[slot].timer,
                              mbedtls_timing_set_delay,
                              mbedtls_timing_get_delay);
    mbedtls_ssl_set_bio(&sessions[slot].ssl, &sessions[slot].client_fd,
                         mbedtls_net_send, mbedtls_net_recv, mbedtls_net_recv_timeout);

    sessions[slot].state = DTLS_SESSION_HANDSHAKING;
    sessions[slot].last_recv_us = esp_timer_get_time();
    ESP_LOGI(TAG, "New connection in slot %d, starting handshake", slot);
}

static void handle_session_io(int idx)
{
    if (sessions[idx].state == DTLS_SESSION_HANDSHAKING) {
        int ret = mbedtls_ssl_handshake(&sessions[idx].ssl);
        if (ret == MBEDTLS_ERR_SSL_WANT_READ || ret == MBEDTLS_ERR_SSL_WANT_WRITE) {
            return;
        }
        if (ret != 0) {
            ESP_LOGW(TAG, "Handshake failed slot %d: -0x%04x", idx, -ret);
            cleanup_session(idx);
            return;
        }

        mbedtls_ssl_session resumed_session;
        mbedtls_ssl_session_init(&resumed_session);
        sessions[idx].session_resumed =
            (mbedtls_ssl_get_session(&sessions[idx].ssl, &resumed_session) == 0);
        mbedtls_ssl_session_free(&resumed_session);

        sessions[idx].state = DTLS_SESSION_ACTIVE;
        sessions[idx].last_recv_us = esp_timer_get_time();
        ESP_LOGI(TAG, "Session %d active (identity='%s', cipher=%s, resumed=%s)",
                 idx, sessions[idx].identity,
                 mbedtls_ssl_get_ciphersuite(&sessions[idx].ssl),
                 sessions[idx].session_resumed ? "yes" : "no");
        return;
    }

    if (sessions[idx].state == DTLS_SESSION_ACTIVE) {
        uint8_t buf[DTLS_MAX_CMD_SIZE];
        int ret = mbedtls_ssl_read(&sessions[idx].ssl, buf, sizeof(buf));

        if (ret == MBEDTLS_ERR_SSL_WANT_READ) {
            return;
        }

        if (ret == MBEDTLS_ERR_SSL_TIMEOUT) {
            ESP_LOGW(TAG, "Session %d timeout", idx);
            cleanup_session(idx);
            return;
        }

        if (ret == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY || ret <= 0) {
            ESP_LOGI(TAG, "Session %d disconnected", idx);
            cleanup_session(idx);
            return;
        }

        sessions[idx].last_recv_us = esp_timer_get_time();

        if ((size_t)ret >= 1 && buf[0] == DTLS_CMD_CTRL_REQUEST) {
            int8_t preempted = -1;
            authority_result_t ar = authority_request(&authority, (uint8_t)idx,
                                                     sessions[idx].priority, &preempted);
            uint8_t resp;
            xSemaphoreTake(ssl_mutex, portMAX_DELAY);
            if (ar == AUTHORITY_RESULT_GRANTED || ar == AUTHORITY_RESULT_PREEMPTED) {
                resp = DTLS_CMD_CTRL_GRANTED;
                mbedtls_ssl_write(&sessions[idx].ssl, &resp, 1);
                if (preempted >= 0 && preempted < max_sessions &&
                    sessions[preempted].state == DTLS_SESSION_ACTIVE) {
                    resp = DTLS_CMD_CTRL_PREEMPTED;
                    mbedtls_ssl_write(&sessions[preempted].ssl, &resp, 1);
                }
            } else {
                resp = DTLS_CMD_CTRL_DENIED;
                mbedtls_ssl_write(&sessions[idx].ssl, &resp, 1);
            }
            xSemaphoreGive(ssl_mutex);
            return;
        }

        if ((size_t)ret >= 1 && buf[0] == DTLS_CMD_CTRL_RELEASE) {
            authority_release(&authority, (uint8_t)idx);
            return;
        }

        if (authority_is_holder(&authority, (uint8_t)idx)) {
            authority_feed(&authority, sessions[idx].last_recv_us);
        }

        if (recv_callback) {
            recv_callback(buf, (size_t)ret, (uint8_t)idx,
                         sessions[idx].peer_ip, 0);
        }
    }
}

static void evict_timed_out_sessions(void)
{
    int64_t now = esp_timer_get_time();
    int64_t timeout_us = (int64_t)current_config.session_timeout_ms * 1000LL;

    for (int i = 0; i < max_sessions; i++) {
        if (sessions[i].state == DTLS_SESSION_HANDSHAKING ||
            sessions[i].state == DTLS_SESSION_ACTIVE) {
            int64_t elapsed = now - sessions[i].last_recv_us;
            if (elapsed > timeout_us) {
                ESP_LOGW(TAG, "Session %d timed out (idle %lld ms)",
                         i, (long long)(elapsed / 1000));
                cleanup_session(i);
            }
        }
    }

    int64_t idle_timeout_us = (int64_t)current_config.authority_idle_timeout_ms * 1000;
    if (idle_timeout_us == 0) idle_timeout_us = (int64_t)DTLS_AUTHORITY_IDLE_MS * 1000;
    if (authority_check_idle(&authority, now, (uint32_t)idle_timeout_us)) {
        ESP_LOGW(TAG, "Authority holder idle-timed out, control released");
    }
}

void dtls_task(void *params)
{
    (void)params;

    while (running) {
        fd_set read_fds;
        FD_ZERO(&read_fds);

        int max_fd = listen_fd.fd;
        if (max_fd >= 0) {
            FD_SET(listen_fd.fd, &read_fds);
        }

        for (int i = 0; i < max_sessions; i++) {
            if (sessions[i].state >= DTLS_SESSION_HANDSHAKING &&
                sessions[i].client_fd.fd >= 0) {
                FD_SET(sessions[i].client_fd.fd, &read_fds);
                if (sessions[i].client_fd.fd > max_fd) {
                    max_fd = sessions[i].client_fd.fd;
                }
            }
        }

        struct timeval tv = { .tv_sec = 0, .tv_usec = 50000 };
        int ready = select(max_fd + 1, &read_fds, NULL, NULL, &tv);

        if (ready > 0) {
            if (listen_fd.fd >= 0 && FD_ISSET(listen_fd.fd, &read_fds)) {
                handle_new_connection();
            }

            for (int i = 0; i < max_sessions; i++) {
                if (sessions[i].state >= DTLS_SESSION_HANDSHAKING &&
                    sessions[i].client_fd.fd >= 0 &&
                    FD_ISSET(sessions[i].client_fd.fd, &read_fds)) {
                    handle_session_io(i);
                }
            }
        }

        evict_timed_out_sessions();
    }

    for (int i = 0; i < max_sessions; i++) {
        cleanup_session(i);
    }
    vTaskDelete(NULL);
}
