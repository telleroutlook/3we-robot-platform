// SPDX-License-Identifier: Apache-2.0
// Integration tests for DTLS handshake + PSK callback + recv dispatcher flow
#include "unity.h"
#include "dtls_transport.h"
#include "mocks/mbedtls_ssl_stubs.h"
#include <string.h>
#include <pthread.h>
#include <unistd.h>

static dtls_config_t test_config;
static volatile int recv_cb_invoked;
static uint8_t recv_buf[256];
static size_t recv_len;

static void setUp_dtls_integration(void) {
    mock_ssl_reset();
    recv_cb_invoked = 0;
    recv_len = 0;
    memset(recv_buf, 0, sizeof(recv_buf));

    memset(&test_config, 0, sizeof(test_config));
    strncpy(test_config.psk_identity, "robot-client", sizeof(test_config.psk_identity) - 1);
    memset(test_config.psk_key, 0xAA, 16);
    test_config.psk_key_len = 16;
    test_config.listen_port = DTLS_CMD_PORT;
    test_config.telemetry_port = DTLS_TELEMETRY_PORT;
    test_config.handshake_timeout_ms = DTLS_HANDSHAKE_TIMEOUT_MS;
    test_config.session_timeout_ms = DTLS_SESSION_TIMEOUT_MS;
}

static void test_recv_callback(const uint8_t *data, size_t len,
                               uint8_t session_id,
                               const char *peer_addr, uint16_t peer_port) {
    (void)session_id; (void)peer_addr; (void)peer_port;
    if (len <= sizeof(recv_buf)) {
        memcpy(recv_buf, data, len);
        recv_len = len;
    }
    recv_cb_invoked = 1;
}

// --- Integration: handshake success triggers connected state ---

static void *run_dtls_task_thread(void *arg) {
    (void)arg;
    dtls_task(NULL);
    return NULL;
}

void test_dtls_handshake_success_sets_connected(void) {
    setUp_dtls_integration();
    mock_ssl_set_handshake_result(0);
    mock_ssl_set_psk_cb_capture(1);
    mock_ssl_set_accept_max_calls(1);

    // After handshake succeeds, read returns peer-close to end inner loop
    mock_ssl_set_read_result(MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY);

    TEST_ASSERT_EQUAL(ESP_OK, dtls_init(&test_config));
    TEST_ASSERT_EQUAL(ESP_OK, dtls_start());

    pthread_t tid;
    pthread_create(&tid, NULL, run_dtls_task_thread, NULL);
    usleep(50000);

    TEST_ASSERT_TRUE(mock_ssl_get_psk_cb_called());

    dtls_stop();
    pthread_join(tid, NULL);
}

// --- Integration: handshake failure does not set connected ---

void test_dtls_handshake_failure_stays_disconnected(void) {
    setUp_dtls_integration();
    mock_ssl_set_handshake_result(-0x7200); // arbitrary fatal error
    mock_ssl_set_psk_cb_capture(0);
    mock_ssl_set_accept_max_calls(1);

    TEST_ASSERT_EQUAL(ESP_OK, dtls_init(&test_config));
    TEST_ASSERT_EQUAL(ESP_OK, dtls_start());

    pthread_t tid;
    pthread_create(&tid, NULL, run_dtls_task_thread, NULL);
    usleep(50000);

    TEST_ASSERT_FALSE(dtls_is_connected());

    dtls_stop();
    pthread_join(tid, NULL);
}

// --- Integration: recv callback receives data after handshake ---

void test_dtls_recv_callback_dispatches_data(void) {
    setUp_dtls_integration();
    mock_ssl_set_handshake_result(0);
    mock_ssl_set_psk_cb_capture(1);
    mock_ssl_set_accept_max_calls(1);

    // First read: CTRL_REQUEST grants authority to this session
    const unsigned char ctrl_req[] = {DTLS_CMD_CTRL_REQUEST};
    // Second read: application motor command data
    const unsigned char motor_cmd[] = {0x10, 0x02, 0x64, 0x00, 0xC8};
    mock_ssl_set_read_data(ctrl_req, sizeof(ctrl_req));
    mock_ssl_set_read_data2(motor_cmd, sizeof(motor_cmd));

    dtls_set_recv_callback(test_recv_callback);
    TEST_ASSERT_EQUAL(ESP_OK, dtls_init(&test_config));
    TEST_ASSERT_EQUAL(ESP_OK, dtls_start());

    pthread_t tid;
    pthread_create(&tid, NULL, run_dtls_task_thread, NULL);
    usleep(50000);

    TEST_ASSERT_TRUE(recv_cb_invoked);
    TEST_ASSERT_EQUAL(sizeof(motor_cmd), recv_len);
    TEST_ASSERT_EQUAL(0, memcmp(motor_cmd, recv_buf, sizeof(motor_cmd)));

    dtls_stop();
    pthread_join(tid, NULL);
}

// --- Integration: PSK identity mismatch is rejected ---

void test_dtls_psk_callback_rejects_wrong_identity(void) {
    setUp_dtls_integration();
    mock_ssl_set_psk_cb_capture(0);
    mock_ssl_set_handshake_result(-0x7780); // handshake fails due to PSK mismatch
    mock_ssl_set_accept_max_calls(1);

    TEST_ASSERT_EQUAL(ESP_OK, dtls_init(&test_config));
    TEST_ASSERT_EQUAL(ESP_OK, dtls_start());

    pthread_t tid;
    pthread_create(&tid, NULL, run_dtls_task_thread, NULL);
    usleep(50000);

    TEST_ASSERT_FALSE(dtls_is_connected());

    dtls_stop();
    pthread_join(tid, NULL);
}
