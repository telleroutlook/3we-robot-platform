// SPDX-License-Identifier: Apache-2.0
#ifndef SPI_STUBS_H
#define SPI_STUBS_H

#include "esp_stubs.h"
#include <stdint.h>
#include <stddef.h>

#define SPI_DMA_DISABLED    0
#define SPI2_HOST           1
#define SPI3_HOST           2

typedef void *spi_device_handle_t;

typedef struct {
    int mosi_io_num;
    int miso_io_num;
    int sclk_io_num;
    int quadwp_io_num;
    int quadhd_io_num;
    int max_transfer_sz;
} spi_bus_config_t;

typedef struct {
    int clock_speed_hz;
    int mode;
    int spics_io_num;
    int queue_size;
} spi_device_interface_config_t;

typedef struct {
    size_t length;
    const void *tx_buffer;
    void *rx_buffer;
} spi_transaction_t;

esp_err_t spi_bus_initialize(int host, const spi_bus_config_t *cfg, int dma);
esp_err_t spi_bus_add_device(int host, const spi_device_interface_config_t *cfg,
                             spi_device_handle_t *handle);
esp_err_t spi_device_polling_transmit(spi_device_handle_t dev, spi_transaction_t *trans);

// Mock control
void mock_spi_reset(void);
void mock_spi_set_rx_byte(uint8_t offset, uint8_t value);
void mock_spi_set_init_error(esp_err_t err);
int mock_spi_get_tx_count(void);
const uint8_t *mock_spi_get_last_tx(size_t *len);

#endif // SPI_STUBS_H
