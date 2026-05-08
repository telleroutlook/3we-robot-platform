// SPDX-License-Identifier: Apache-2.0
#ifndef UDP_TRANSPORT_H
#define UDP_TRANSPORT_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define UDP_CMD_PORT    8888
#define UDP_TELEM_PORT  9999

typedef void (*udp_recv_callback_t)(const uint8_t *data, size_t len,
                                    const char *src_ip, uint16_t src_port);

typedef struct {
    uint16_t cmd_port;
    uint16_t telemetry_port;
    uint32_t timeout_ms;
} udp_transport_config_t;

esp_err_t udp_transport_init(const udp_transport_config_t *config);
esp_err_t udp_transport_send_telemetry(const uint8_t *data, size_t len);
void udp_transport_set_recv_callback(udp_recv_callback_t cb);
bool udp_transport_has_client(void);
void udp_transport_task(void *params);

#endif // UDP_TRANSPORT_H
