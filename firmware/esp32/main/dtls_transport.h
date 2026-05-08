// SPDX-License-Identifier: Apache-2.0
#ifndef DTLS_TRANSPORT_H
#define DTLS_TRANSPORT_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    char psk_identity[32];
    uint8_t psk_key[32];
    uint8_t psk_key_len;
    uint16_t listen_port;       // Default: 8888 (commands)
    uint16_t telemetry_port;    // Default: 9999 (telemetry)
    uint32_t handshake_timeout_ms;
    uint32_t session_timeout_ms;
} dtls_config_t;

typedef void (*dtls_recv_callback_t)(const uint8_t *data, size_t len,
                                     const char *peer_addr, uint16_t peer_port);

esp_err_t dtls_init(const dtls_config_t *config);
esp_err_t dtls_start(void);
void dtls_stop(void);
esp_err_t dtls_send(const uint8_t *data, size_t len);
void dtls_set_recv_callback(dtls_recv_callback_t cb);
bool dtls_is_connected(void);
bool dtls_session_was_resumed(void);
void dtls_task(void *params);

// Default configuration values
#define DTLS_CMD_PORT               5684
#define DTLS_TELEMETRY_PORT         5685
#define DTLS_HANDSHAKE_TIMEOUT_MS   5000
#define DTLS_SESSION_TIMEOUT_MS     30000

#endif // DTLS_TRANSPORT_H
