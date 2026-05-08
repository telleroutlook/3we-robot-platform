// SPDX-License-Identifier: Apache-2.0
// Unit tests for DTLS transport (dtls_transport.c)
// Tests configuration validation and state management at the API boundary.
#include "unity.h"
#include "dtls_transport.h"
#include <string.h>

// Since dtls_transport.c uses many mbedtls networking functions that are hard
// to mock cleanly in a host-side build, we test the public API contract:
// config validation, state queries, and callback registration.

static dtls_config_t valid_config;

void setUp_dtls(void) {
    memset(&valid_config, 0, sizeof(valid_config));
    strncpy(valid_config.psk_identity, "robot-client", sizeof(valid_config.psk_identity) - 1);
    memset(valid_config.psk_key, 0xAA, 16);
    valid_config.psk_key_len = 16;
    valid_config.listen_port = DTLS_CMD_PORT;
    valid_config.telemetry_port = DTLS_TELEMETRY_PORT;
    valid_config.handshake_timeout_ms = DTLS_HANDSHAKE_TIMEOUT_MS;
    valid_config.session_timeout_ms = DTLS_SESSION_TIMEOUT_MS;
}

// --- dtls_init tests ---

void test_dtls_init_rejects_null_config(void) {
    setUp_dtls();
    esp_err_t err = dtls_init(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_dtls_init_accepts_valid_config(void) {
    setUp_dtls();
    esp_err_t err = dtls_init(&valid_config);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    dtls_stop();
}

// --- dtls_is_connected tests ---

void test_dtls_not_connected_initially(void) {
    setUp_dtls();
    dtls_init(&valid_config);
    TEST_ASSERT_FALSE(dtls_is_connected());
    dtls_stop();
}

// --- dtls_send tests ---

void test_dtls_send_rejects_when_not_connected(void) {
    setUp_dtls();
    dtls_init(&valid_config);

    uint8_t data[] = {0x01, 0x02, 0x03};
    esp_err_t err = dtls_send(data, sizeof(data));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
    dtls_stop();
}

// --- dtls_set_recv_callback tests ---

static bool callback_invoked = false;
static void test_recv_cb(const uint8_t *data, size_t len,
                         const char *peer_addr, uint16_t peer_port) {
    (void)data; (void)len; (void)peer_addr; (void)peer_port;
    callback_invoked = true;
}

void test_dtls_callback_registration(void) {
    setUp_dtls();
    callback_invoked = false;
    dtls_set_recv_callback(test_recv_cb);
    // Callback is registered — we can't easily trigger it without a real
    // DTLS session, but we verify it doesn't crash.
    dtls_set_recv_callback(NULL);
}

// --- Config value tests ---

void test_dtls_default_ports(void) {
    TEST_ASSERT_EQUAL(5684, DTLS_CMD_PORT);
    TEST_ASSERT_EQUAL(5685, DTLS_TELEMETRY_PORT);
}

void test_dtls_default_timeouts(void) {
    TEST_ASSERT_EQUAL(5000, DTLS_HANDSHAKE_TIMEOUT_MS);
    TEST_ASSERT_EQUAL(30000, DTLS_SESSION_TIMEOUT_MS);
}
