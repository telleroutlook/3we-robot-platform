// SPDX-License-Identifier: Apache-2.0
#include "spi_stubs.h"
#include <string.h>

#define MAX_TX_LEN 32

static esp_err_t init_error = ESP_OK;
static int tx_count = 0;
static uint8_t last_tx[MAX_TX_LEN];
static size_t last_tx_len = 0;
static uint8_t rx_data[MAX_TX_LEN];

void mock_spi_reset(void)
{
    init_error = ESP_OK;
    tx_count = 0;
    last_tx_len = 0;
    memset(last_tx, 0, sizeof(last_tx));
    memset(rx_data, 0, sizeof(rx_data));
}

void mock_spi_set_rx_byte(uint8_t offset, uint8_t value)
{
    if (offset < MAX_TX_LEN) rx_data[offset] = value;
}

void mock_spi_set_init_error(esp_err_t err)
{
    init_error = err;
}

int mock_spi_get_tx_count(void)
{
    return tx_count;
}

const uint8_t *mock_spi_get_last_tx(size_t *len)
{
    *len = last_tx_len;
    return last_tx;
}

esp_err_t spi_bus_initialize(int host, const spi_bus_config_t *cfg, int dma)
{
    (void)host; (void)cfg; (void)dma;
    return init_error;
}

esp_err_t spi_bus_add_device(int host, const spi_device_interface_config_t *cfg,
                             spi_device_handle_t *handle)
{
    (void)host; (void)cfg;
    *handle = (spi_device_handle_t)0x1;
    return init_error;
}

esp_err_t spi_device_polling_transmit(spi_device_handle_t dev, spi_transaction_t *trans)
{
    (void)dev;
    tx_count++;

    size_t byte_len = (trans->length + 7) / 8;
    if (trans->tx_buffer && byte_len <= MAX_TX_LEN) {
        memcpy(last_tx, trans->tx_buffer, byte_len);
        last_tx_len = byte_len;
    }

    if (trans->rx_buffer && byte_len <= MAX_TX_LEN) {
        memcpy(trans->rx_buffer, rx_data, byte_len);
    }

    return ESP_OK;
}
