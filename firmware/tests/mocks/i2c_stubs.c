// SPDX-License-Identifier: Apache-2.0
#include "i2c_stubs.h"
#include <string.h>

#define MAX_DEVICES 16
#define MAX_REGS    256
#define MAX_DATA    64

typedef struct {
    uint8_t addr;
    uint8_t reg_data[MAX_REGS][MAX_DATA];
    size_t  reg_data_len[MAX_REGS];
    esp_err_t read_error;
    esp_err_t write_error;
    int write_count;
    uint8_t last_write[MAX_DATA];
    size_t last_write_len;
} i2c_device_mock_t;

static i2c_device_mock_t devices[MAX_DEVICES];
static int device_count = 0;

static i2c_device_mock_t *find_device(uint8_t addr)
{
    for (int i = 0; i < device_count; i++) {
        if (devices[i].addr == addr) return &devices[i];
    }
    return NULL;
}

static i2c_device_mock_t *get_or_create_device(uint8_t addr)
{
    i2c_device_mock_t *dev = find_device(addr);
    if (dev) return dev;
    if (device_count >= MAX_DEVICES) return NULL;
    dev = &devices[device_count++];
    memset(dev, 0, sizeof(*dev));
    dev->addr = addr;
    return dev;
}

void mock_i2c_reset(void)
{
    memset(devices, 0, sizeof(devices));
    device_count = 0;
}

void mock_i2c_set_read_data(uint8_t addr, uint8_t reg, const uint8_t *data, size_t len)
{
    i2c_device_mock_t *dev = get_or_create_device(addr);
    if (!dev || len > MAX_DATA) return;
    memcpy(dev->reg_data[reg], data, len);
    dev->reg_data_len[reg] = len;
}

void mock_i2c_set_read_error(uint8_t addr, esp_err_t err)
{
    i2c_device_mock_t *dev = get_or_create_device(addr);
    if (dev) dev->read_error = err;
}

void mock_i2c_set_write_error(uint8_t addr, esp_err_t err)
{
    i2c_device_mock_t *dev = get_or_create_device(addr);
    if (dev) dev->write_error = err;
}

int mock_i2c_get_write_count(uint8_t addr)
{
    i2c_device_mock_t *dev = find_device(addr);
    return dev ? dev->write_count : 0;
}

const uint8_t *mock_i2c_get_last_write(uint8_t addr, size_t *len)
{
    i2c_device_mock_t *dev = find_device(addr);
    if (!dev) { *len = 0; return NULL; }
    *len = dev->last_write_len;
    return dev->last_write;
}

esp_err_t i2c_param_config(int port, const i2c_config_t *conf)
{
    (void)port; (void)conf;
    return ESP_OK;
}

esp_err_t i2c_driver_install(int port, int mode, int slv_rx, int slv_tx, int flags)
{
    (void)port; (void)mode; (void)slv_rx; (void)slv_tx; (void)flags;
    return ESP_OK;
}

esp_err_t i2c_driver_delete(int port)
{
    (void)port;
    return ESP_OK;
}

void esp_rom_delay_us(uint32_t us)
{
    (void)us;
}

esp_err_t i2c_master_write_to_device(int port, uint8_t addr,
                                      const uint8_t *data, size_t len, int timeout)
{
    (void)port; (void)timeout;
    i2c_device_mock_t *dev = get_or_create_device(addr);
    if (!dev) return ESP_FAIL;
    if (dev->write_error != ESP_OK) return dev->write_error;

    dev->write_count++;
    if (len <= MAX_DATA) {
        memcpy(dev->last_write, data, len);
        dev->last_write_len = len;
    }
    return ESP_OK;
}

esp_err_t i2c_master_write_read_device(int port, uint8_t addr,
                                        const uint8_t *write_data, size_t write_len,
                                        uint8_t *read_data, size_t read_len, int timeout)
{
    (void)port; (void)timeout;
    i2c_device_mock_t *dev = find_device(addr);
    if (!dev) {
        dev = get_or_create_device(addr);
        if (!dev) return ESP_FAIL;
    }
    if (dev->read_error != ESP_OK) return dev->read_error;

    uint8_t reg = (write_len > 0) ? write_data[0] : 0;
    size_t avail = dev->reg_data_len[reg];
    if (avail > 0 && avail >= read_len) {
        memcpy(read_data, dev->reg_data[reg], read_len);
    } else {
        memset(read_data, 0, read_len);
    }
    return ESP_OK;
}
