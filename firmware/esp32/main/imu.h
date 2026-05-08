// SPDX-License-Identifier: Apache-2.0
#ifndef IMU_H
#define IMU_H

#include "esp_err.h"

typedef struct {
    float w, x, y, z;
} quaternion_t;

typedef struct {
    float roll, pitch, yaw;  // radians
} euler_t;

typedef struct {
    float x, y, z;
} vec3_t;

esp_err_t imu_init(void);
esp_err_t imu_read_quaternion(quaternion_t *q);
esp_err_t imu_read_euler(euler_t *e);
esp_err_t imu_read_angular_velocity(vec3_t *gyro);
esp_err_t imu_read_linear_accel(vec3_t *accel);
bool imu_is_calibrated(void);

#endif // IMU_H
