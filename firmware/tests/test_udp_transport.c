// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "udp_transport.h"
#include "lwip/sockets.h"

void test_udp_init_rejects_null_config(void)
{
    mock_lwip_reset();
    esp_err_t err = udp_transport_init(NULL);
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_ARG, err);
}

void test_udp_has_client_initially_false(void)
{
    mock_lwip_reset();
    TEST_ASSERT_FALSE(udp_transport_has_client());
}

void test_udp_init_fails_socket_create(void)
{
    mock_lwip_reset();
    mock_lwip_set_socket_fail(true);
    udp_transport_config_t config = {
        .cmd_port = 8888,
        .telemetry_port = 9999,
        .timeout_ms = 1000,
    };
    esp_err_t err = udp_transport_init(&config);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

void test_udp_init_fails_bind(void)
{
    mock_lwip_reset();
    mock_lwip_set_bind_fail(true);
    udp_transport_config_t config = {
        .cmd_port = 8888,
        .telemetry_port = 9999,
        .timeout_ms = 1000,
    };
    esp_err_t err = udp_transport_init(&config);
    TEST_ASSERT_EQUAL(ESP_FAIL, err);
}

void test_udp_init_success(void)
{
    mock_lwip_reset();
    udp_transport_config_t config = {
        .cmd_port = 8888,
        .telemetry_port = 9999,
        .timeout_ms = 1000,
    };
    esp_err_t err = udp_transport_init(&config);
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_udp_send_telemetry_no_client(void)
{
    mock_lwip_reset();
    uint8_t data[] = {0x01, 0x02};
    esp_err_t err = udp_transport_send_telemetry(data, sizeof(data));
    TEST_ASSERT_EQUAL(ESP_ERR_INVALID_STATE, err);
}

void test_udp_set_recv_callback(void)
{
    mock_lwip_reset();
    udp_transport_set_recv_callback(NULL);
}
