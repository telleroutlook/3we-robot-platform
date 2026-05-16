// SPDX-License-Identifier: Apache-2.0
#include "udp_transport.h"
#include "safety.h"

#include "esp_log.h"
#include "esp_timer.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "udp_xport";

static portMUX_TYPE udp_spinlock = portMUX_INITIALIZER_UNLOCKED;
static int cmd_sock = -1;
static int telem_sock = -1;
static udp_transport_config_t cfg;
static udp_recv_callback_t recv_callback = NULL;
static struct sockaddr_in last_client_addr;
static bool client_known = false;
static int64_t last_recv_time = 0;

esp_err_t udp_transport_init(const udp_transport_config_t *config)
{
    if (!config) return ESP_ERR_INVALID_ARG;
    memcpy(&cfg, config, sizeof(cfg));

    // Create command receive socket
    cmd_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (cmd_sock < 0) {
        ESP_LOGE(TAG, "Failed to create cmd socket");
        return ESP_FAIL;
    }

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(config->cmd_port),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };

    if (bind(cmd_sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        ESP_LOGE(TAG, "Bind cmd port %d failed", config->cmd_port);
        close(cmd_sock);
        cmd_sock = -1;
        return ESP_FAIL;
    }

    // Set receive timeout
    struct timeval tv = {
        .tv_sec = config->timeout_ms / 1000,
        .tv_usec = (config->timeout_ms % 1000) * 1000,
    };
    setsockopt(cmd_sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    // Create telemetry send socket
    telem_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (telem_sock < 0) {
        ESP_LOGE(TAG, "Failed to create telemetry socket");
        close(cmd_sock);
        cmd_sock = -1;
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "UDP transport initialized (cmd:%d, telem:%d)",
             config->cmd_port, config->telemetry_port);
    return ESP_OK;
}

esp_err_t udp_transport_send_telemetry(const uint8_t *data, size_t len)
{
    portENTER_CRITICAL(&udp_spinlock);
    if (!client_known || telem_sock < 0) {
        portEXIT_CRITICAL(&udp_spinlock);
        return ESP_ERR_INVALID_STATE;
    }
    struct sockaddr_in dest = last_client_addr;
    portEXIT_CRITICAL(&udp_spinlock);

    dest.sin_port = htons(cfg.telemetry_port);

    int sent = sendto(telem_sock, data, len, 0,
                      (struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) return ESP_FAIL;
    return ESP_OK;
}

void udp_transport_set_recv_callback(udp_recv_callback_t cb)
{
    portENTER_CRITICAL(&udp_spinlock);
    recv_callback = cb;
    portEXIT_CRITICAL(&udp_spinlock);
}

bool udp_transport_has_client(void)
{
    portENTER_CRITICAL(&udp_spinlock);
    if (!client_known) {
        portEXIT_CRITICAL(&udp_spinlock);
        return false;
    }
    int64_t t = last_recv_time;
    portEXIT_CRITICAL(&udp_spinlock);
    int64_t now = esp_timer_get_time();
    return (now - t) < (cfg.timeout_ms * 1000LL);
}

void udp_transport_task(void *params)
{
    uint8_t buf[256];
    struct sockaddr_in src_addr;
    socklen_t addr_len = sizeof(src_addr);

    while (1) {
        int len = recvfrom(cmd_sock, buf, sizeof(buf), 0,
                           (struct sockaddr *)&src_addr, &addr_len);

        if (len > 0) {
            portENTER_CRITICAL(&udp_spinlock);
            last_client_addr = src_addr;
            client_known = true;
            last_recv_time = esp_timer_get_time();
            portEXIT_CRITICAL(&udp_spinlock);

            char ip_str[INET_ADDRSTRLEN];
            inet_ntoa_r(src_addr.sin_addr, ip_str, sizeof(ip_str));

#ifndef CONFIG_ROBOT_ALLOW_PLAINTEXT_CTRL
            // Without plaintext control enabled, UDP is telemetry-only.
            // Drop all received data to prevent unauthenticated command dispatch.
            ESP_LOGD(TAG, "UDP rx %d bytes from %s (dropped: plaintext ctrl disabled)", len, ip_str);
#else
            udp_recv_callback_t cb;
            portENTER_CRITICAL(&udp_spinlock);
            cb = recv_callback;
            portEXIT_CRITICAL(&udp_spinlock);
            if (cb) {
                cb(buf, (size_t)len, ip_str, ntohs(src_addr.sin_port));
            }
#endif
        }

        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
