// SPDX-License-Identifier: Apache-2.0
#include "imu.h"
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "esp_log.h"

#include <string.h>

static const char *TAG = "imu";

#define BNO055_CHIP_ID_REG      0x00
#define BNO055_CHIP_ID_VAL      0xA0
#define BNO055_OPR_MODE_REG     0x3D
#define BNO055_OPR_MODE_NDOF    0x0C
#define BNO055_OPR_MODE_CONFIG  0x00
#define BNO055_QUA_DATA_W_REG   0x20
#define BNO055_EUL_DATA_H_REG   0x1A
#define BNO055_GYR_DATA_X_REG   0x14
#define BNO055_LIA_DATA_X_REG   0x28
#define BNO055_CALIB_STAT_REG   0x35

#define I2C_PORT    I2C_NUM_0
#define I2C_TIMEOUT pdMS_TO_TICKS(100)

static uint8_t imu_addr = IMU_ADDR;

static esp_err_t i2c_read_reg(uint8_t reg, uint8_t *data, size_t len)
{
    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;
    esp_err_t err = i2c_master_write_read_device(I2C_PORT, imu_addr, &reg, 1, data, len, I2C_TIMEOUT);
    i2c_bus_unlock();
    return err;
}

static esp_err_t i2c_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = { reg, val };
    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;
    esp_err_t err = i2c_master_write_to_device(I2C_PORT, imu_addr, buf, 2, I2C_TIMEOUT);
    i2c_bus_unlock();
    return err;
}

esp_err_t imu_init(void)
{
    // Probe for BNO055
    uint8_t chip_id = 0;
    esp_err_t err = i2c_read_reg(BNO055_CHIP_ID_REG, &chip_id, 1);
    if (err != ESP_OK || chip_id != BNO055_CHIP_ID_VAL) {
        imu_addr = IMU_ADDR_ALT;
        err = i2c_read_reg(BNO055_CHIP_ID_REG, &chip_id, 1);
        if (err != ESP_OK || chip_id != BNO055_CHIP_ID_VAL) {
            ESP_LOGE(TAG, "BNO055 not found (id=0x%02X)", chip_id);
            return ESP_ERR_NOT_FOUND;
        }
    }

    // Configure NDOF fusion mode
    err = i2c_write_reg(BNO055_OPR_MODE_REG, BNO055_OPR_MODE_CONFIG);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set CONFIG mode");
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(25));
    err = i2c_write_reg(BNO055_OPR_MODE_REG, BNO055_OPR_MODE_NDOF);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set NDOF mode");
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    ESP_LOGI(TAG, "BNO055 initialized (addr=0x%02X, NDOF mode)", imu_addr);
    return ESP_OK;
}

esp_err_t imu_read_quaternion(quaternion_t *q)
{
    uint8_t buf[8];
    esp_err_t err = i2c_read_reg(BNO055_QUA_DATA_W_REG, buf, 8);
    if (err != ESP_OK) return err;

    const float scale = 1.0f / (1 << 14);
    q->w = (float)((int16_t)(buf[1] << 8 | buf[0])) * scale;
    q->x = (float)((int16_t)(buf[3] << 8 | buf[2])) * scale;
    q->y = (float)((int16_t)(buf[5] << 8 | buf[4])) * scale;
    q->z = (float)((int16_t)(buf[7] << 8 | buf[6])) * scale;
    return ESP_OK;
}

esp_err_t imu_read_euler(euler_t *e)
{
    uint8_t buf[6];
    esp_err_t err = i2c_read_reg(BNO055_EUL_DATA_H_REG, buf, 6);
    if (err != ESP_OK) return err;

    const float scale = 1.0f / 16.0f;  // degrees
    const float deg2rad = 3.14159265f / 180.0f;
    e->yaw   = (float)((int16_t)(buf[1] << 8 | buf[0])) * scale * deg2rad;
    e->roll  = (float)((int16_t)(buf[3] << 8 | buf[2])) * scale * deg2rad;
    e->pitch = (float)((int16_t)(buf[5] << 8 | buf[4])) * scale * deg2rad;
    return ESP_OK;
}

esp_err_t imu_read_angular_velocity(vec3_t *gyro)
{
    uint8_t buf[6];
    esp_err_t err = i2c_read_reg(BNO055_GYR_DATA_X_REG, buf, 6);
    if (err != ESP_OK) return err;

    const float scale = 1.0f / 16.0f;  // dps
    const float dps2rps = 3.14159265f / 180.0f;
    gyro->x = (float)((int16_t)(buf[1] << 8 | buf[0])) * scale * dps2rps;
    gyro->y = (float)((int16_t)(buf[3] << 8 | buf[2])) * scale * dps2rps;
    gyro->z = (float)((int16_t)(buf[5] << 8 | buf[4])) * scale * dps2rps;
    return ESP_OK;
}

esp_err_t imu_read_linear_accel(vec3_t *accel)
{
    uint8_t buf[6];
    esp_err_t err = i2c_read_reg(BNO055_LIA_DATA_X_REG, buf, 6);
    if (err != ESP_OK) return err;

    const float scale = 1.0f / 100.0f;  // m/s^2
    accel->x = (float)((int16_t)(buf[1] << 8 | buf[0])) * scale;
    accel->y = (float)((int16_t)(buf[3] << 8 | buf[2])) * scale;
    accel->z = (float)((int16_t)(buf[5] << 8 | buf[4])) * scale;
    return ESP_OK;
}

bool imu_is_calibrated(void)
{
    uint8_t stat = 0;
    if (i2c_read_reg(BNO055_CALIB_STAT_REG, &stat, 1) != ESP_OK) return false;
    // All 4 subsystems calibrated (sys, gyro, accel, mag all == 3)
    return stat == 0xFF;
}
