// SPDX-License-Identifier: Apache-2.0
#ifndef DTLS_TRANSPORT_H
#define DTLS_TRANSPORT_H

#include "esp_err.h"
#include "dtls_authority.h"
#include <stdint.h>
#include <stdbool.h>

#define DTLS_MAX_OPERATORS  8

typedef enum {
    DTLS_SESSION_EMPTY = 0,
    DTLS_SESSION_HANDSHAKING,
    DTLS_SESSION_ACTIVE,
    DTLS_SESSION_CLOSING,
} dtls_session_state_t;

typedef struct {
    char      identity[32];
    uint8_t   psk_key[32];
    uint8_t   psk_key_len;
    uint8_t   priority;
    dtls_role_t role;
} dtls_operator_entry_t;

typedef struct {
    char psk_identity[32];
    uint8_t psk_key[32];
    uint8_t psk_key_len;
    uint16_t listen_port;
    uint16_t telemetry_port;
    uint32_t handshake_timeout_ms;
    uint32_t session_timeout_ms;
    uint8_t  max_sessions;
    uint32_t authority_idle_timeout_ms;
} dtls_config_t;

typedef void (*dtls_recv_callback_t)(const uint8_t *data, size_t len,
                                     uint8_t session_id,
                                     const char *peer_addr, uint16_t peer_port);

esp_err_t dtls_init(const dtls_config_t *config);
esp_err_t dtls_start(void);
void dtls_stop(void);

esp_err_t dtls_send(const uint8_t *data, size_t len);
esp_err_t dtls_send_to_session(uint8_t session_id, const uint8_t *data, size_t len);
esp_err_t dtls_broadcast(const uint8_t *data, size_t len);

void dtls_set_recv_callback(dtls_recv_callback_t cb);

bool dtls_is_connected(void);
bool dtls_session_was_resumed(void);
uint8_t dtls_active_session_count(void);
int8_t dtls_get_authority_holder(void);
bool dtls_session_has_authority(uint8_t session_id);
dtls_session_state_t dtls_get_session_state(uint8_t session_id);

esp_err_t dtls_register_operator(const dtls_operator_entry_t *op);
esp_err_t dtls_load_operators_from_nvs(void);
esp_err_t dtls_save_operator_to_nvs(const dtls_operator_entry_t *op);

void dtls_task(void *params);

#define DTLS_CMD_PORT               5684
#define DTLS_TELEMETRY_PORT         5685
#define DTLS_HANDSHAKE_TIMEOUT_MS   5000
#define DTLS_SESSION_TIMEOUT_MS     30000
#define DTLS_AUTHORITY_IDLE_MS      5000
#define DTLS_MAX_CMD_SIZE           512

#define DTLS_CMD_CTRL_REQUEST       0x01
#define DTLS_CMD_CTRL_RELEASE       0x02
#define DTLS_CMD_CTRL_GRANTED       0x03
#define DTLS_CMD_CTRL_DENIED        0x04
#define DTLS_CMD_CTRL_PREEMPTED     0x05

#endif // DTLS_TRANSPORT_H
