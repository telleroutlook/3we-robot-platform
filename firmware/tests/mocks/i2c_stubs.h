// SPDX-License-Identifier: Apache-2.0
#ifndef I2C_STUBS_H
#define I2C_STUBS_H

#include "esp_stubs.h"
#include <stdint.h>
#include <stddef.h>

#define I2C_NUM_0           0
#define I2C_MODE_MASTER     0
#define portMAX_DELAY       0xFFFFFFFF

typedef struct {
    int mode;
    int sda_io_num;
    int scl_io_num;
    int sda_pullup_en;
    int scl_pullup_en;
    struct { int clk_speed; } master;
} i2c_config_t;

esp_err_t i2c_param_config(int port, const i2c_config_t *conf);
esp_err_t i2c_driver_install(int port, int mode, int slv_rx, int slv_tx, int flags);
esp_err_t i2c_driver_delete(int port);
void esp_rom_delay_us(uint32_t us);
esp_err_t i2c_master_write_to_device(int port, uint8_t addr,
                                      const uint8_t *data, size_t len, int timeout);
esp_err_t i2c_master_write_read_device(int port, uint8_t addr,
                                        const uint8_t *write_data, size_t write_len,
                                        uint8_t *read_data, size_t read_len, int timeout);

// Mock control
void mock_i2c_reset(void);
void mock_i2c_set_read_data(uint8_t addr, uint8_t reg, const uint8_t *data, size_t len);
void mock_i2c_set_read_error(uint8_t addr, esp_err_t err);
void mock_i2c_set_write_error(uint8_t addr, esp_err_t err);
int mock_i2c_get_write_count(uint8_t addr);
const uint8_t *mock_i2c_get_last_write(uint8_t addr, size_t *len);

#endif // I2C_STUBS_H
