// SPDX-License-Identifier: Apache-2.0
#include "udp_transport.h"

#include "esp_log.h"
#include "esp_timer.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "udp_xport";

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
    if (!client_known || telem_sock < 0) return ESP_ERR_INVALID_STATE;

    struct sockaddr_in dest = last_client_addr;
    dest.sin_port = htons(cfg.telemetry_port);

    int sent = sendto(telem_sock, data, len, 0,
                      (struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) return ESP_FAIL;
    return ESP_OK;
}

void udp_transport_set_recv_callback(udp_recv_callback_t cb)
{
    recv_callback = cb;
}

bool udp_transport_has_client(void)
{
    if (!client_known) return false;
    int64_t now = esp_timer_get_time();
    return (now - last_recv_time) < (cfg.timeout_ms * 1000LL);
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
            last_client_addr = src_addr;
            client_known = true;
            last_recv_time = esp_timer_get_time();

            char ip_str[INET_ADDRSTRLEN];
            inet_ntoa_r(src_addr.sin_addr, ip_str, sizeof(ip_str));

            if (recv_callback) {
                recv_callback(buf, (size_t)len, ip_str, ntohs(src_addr.sin_port));
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
