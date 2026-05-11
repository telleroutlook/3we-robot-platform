// SPDX-License-Identifier: Apache-2.0
#include "imu.h"
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"

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
#define BNO055_ACCEL_OFFSET_REG 0x55
#define BNO055_CALIB_DATA_LEN   22

#define I2C_PORT    I2C_NUM_0
#define I2C_TIMEOUT pdMS_TO_TICKS(100)

static uint8_t imu_addr = IMU_ADDR;
static bool calibration_saved = false;

static esp_err_t imu_load_calibration(void)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open("imu_cal", NVS_READONLY, &handle);
    if (err != ESP_OK) return err;

    uint8_t cal_data[BNO055_CALIB_DATA_LEN];
    size_t len = BNO055_CALIB_DATA_LEN;
    err = nvs_get_blob(handle, "offsets", cal_data, &len);
    nvs_close(handle);
    if (err != ESP_OK || len != BNO055_CALIB_DATA_LEN) return ESP_ERR_INVALID_SIZE;

    err = i2c_write_reg(BNO055_OPR_MODE_REG, BNO055_OPR_MODE_CONFIG);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(25));

    for (int i = 0; i < BNO055_CALIB_DATA_LEN; i++) {
        err = i2c_write_reg(BNO055_ACCEL_OFFSET_REG + i, cal_data[i]);
        if (err != ESP_OK) return err;
    }

    ESP_LOGI(TAG, "Calibration loaded from NVS");
    return ESP_OK;
}

static esp_err_t imu_save_calibration(void)
{
    uint8_t cal_data[BNO055_CALIB_DATA_LEN];
    esp_err_t err = i2c_write_reg(BNO055_OPR_MODE_REG, BNO055_OPR_MODE_CONFIG);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(25));

    err = i2c_read_reg(BNO055_ACCEL_OFFSET_REG, cal_data, BNO055_CALIB_DATA_LEN);
    if (err != ESP_OK) goto restore_mode;

    nvs_handle_t handle;
    err = nvs_open("imu_cal", NVS_READWRITE, &handle);
    if (err != ESP_OK) goto restore_mode;

    err = nvs_set_blob(handle, "offsets", cal_data, BNO055_CALIB_DATA_LEN);
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);

    if (err == ESP_OK) ESP_LOGI(TAG, "Calibration saved to NVS");

restore_mode:
    i2c_write_reg(BNO055_OPR_MODE_REG, BNO055_OPR_MODE_NDOF);
    vTaskDelay(pdMS_TO_TICKS(20));
    return err;
}

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

    // Attempt to restore saved calibration offsets
    if (imu_load_calibration() == ESP_OK) {
        calibration_saved = true;
    }

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
    bool fully_calibrated = (stat == 0xFF);
    if (fully_calibrated && !calibration_saved) {
        imu_save_calibration();
        calibration_saved = true;
    }
    return fully_calibrated;
}
