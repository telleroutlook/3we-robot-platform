// SPDX-License-Identifier: Apache-2.0
// Unit tests for IMU driver (BNO055 over I2C)
#include "unity.h"
#include "imu.h"
#include "pin_definitions.h"
#include "i2c_stubs.h"
#include "esp_stubs.h"
#include "freertos/semphr.h"

#include <string.h>
#include <math.h>

#define FLOAT_TOLERANCE 0.001f

// BNO055 registers (mirrored from imu.c for test clarity)
#define BNO055_CHIP_ID_REG      0x00
#define BNO055_CHIP_ID_VAL      0xA0
#define BNO055_QUA_DATA_W_REG   0x20
#define BNO055_EUL_DATA_H_REG   0x1A
#define BNO055_GYR_DATA_X_REG   0x14
#define BNO055_LIA_DATA_X_REG   0x28
#define BNO055_CALIB_STAT_REG   0x35

// i2c_bus_get_mutex is already provided by test_payload_hotplug.c

// Helper: set up mock so imu_init() will succeed regardless of imu_addr state.
// The static imu_addr in imu.c may be 0x28 or 0x29 depending on prior tests,
// so we provide valid chip_id at both addresses.
static void setup_imu_init_success(void)
{
    uint8_t chip_id = BNO055_CHIP_ID_VAL;
    mock_i2c_set_read_data(IMU_ADDR, BNO055_CHIP_ID_REG, &chip_id, 1);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_CHIP_ID_REG, &chip_id, 1);
}

// ---------------------------------------------------------------------------
// Test: imu_init finds BNO055 at primary address 0x28
// ---------------------------------------------------------------------------
void test_imu_init_primary_addr(void)
{
    mock_i2c_reset();
    uint8_t chip_id = BNO055_CHIP_ID_VAL;
    mock_i2c_set_read_data(IMU_ADDR, BNO055_CHIP_ID_REG, &chip_id, 1);

    esp_err_t ret = imu_init();
    TEST_ASSERT_EQUAL(ESP_OK, ret);
}

// ---------------------------------------------------------------------------
// Test: imu_init fails at primary, succeeds at alternate address 0x29
// ---------------------------------------------------------------------------
void test_imu_init_alt_addr(void)
{
    mock_i2c_reset();
    // Primary address returns wrong chip ID
    uint8_t wrong_id = 0x00;
    mock_i2c_set_read_data(IMU_ADDR, BNO055_CHIP_ID_REG, &wrong_id, 1);
    // Alternate address returns correct chip ID
    uint8_t chip_id = BNO055_CHIP_ID_VAL;
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_CHIP_ID_REG, &chip_id, 1);

    esp_err_t ret = imu_init();
    TEST_ASSERT_EQUAL(ESP_OK, ret);
}

// ---------------------------------------------------------------------------
// Test: imu_init returns NOT_FOUND when neither address responds correctly
// ---------------------------------------------------------------------------
void test_imu_init_not_found(void)
{
    mock_i2c_reset();
    // Both addresses return wrong chip ID (mock default is 0x00)

    esp_err_t ret = imu_init();
    TEST_ASSERT_EQUAL(ESP_ERR_NOT_FOUND, ret);
}

// ---------------------------------------------------------------------------
// Test: imu_read_quaternion converts raw int16 to float correctly
// raw 16384 (0x4000) → 1.0 (scale = 1/16384)
// ---------------------------------------------------------------------------
void test_imu_read_quaternion(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // 8 bytes at reg 0x20: w, x, y, z (each 2 bytes little-endian int16)
    // w=16384(0x4000), x=0, y=8192(0x2000), z=-16384(0xC000)
    uint8_t quat_data[8] = {
        0x00, 0x40,  // w = 16384 → 1.0
        0x00, 0x00,  // x = 0 → 0.0
        0x00, 0x20,  // y = 8192 → 0.5
        0x00, 0xC0,  // z = -16384 → -1.0
    };
    mock_i2c_set_read_data(IMU_ADDR, BNO055_QUA_DATA_W_REG, quat_data, 8);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_QUA_DATA_W_REG, quat_data, 8);

    quaternion_t q;
    esp_err_t ret = imu_read_quaternion(&q);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, q.w);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, q.x);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.5f, q.y);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, q.z);
}

// ---------------------------------------------------------------------------
// Test: imu_read_quaternion handles negative int16 values
// ---------------------------------------------------------------------------
void test_imu_read_quaternion_negative(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // w=-8192(0xE000), x=-1(0xFFFF), y=1(0x0001), z=0
    uint8_t quat_data[8] = {
        0x00, 0xE0,  // w = -8192 → -0.5
        0xFF, 0xFF,  // x = -1 → -1/16384 ≈ -0.0000610
        0x01, 0x00,  // y = 1 → 1/16384 ≈ 0.0000610
        0x00, 0x00,  // z = 0 → 0.0
    };
    mock_i2c_set_read_data(IMU_ADDR, BNO055_QUA_DATA_W_REG, quat_data, 8);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_QUA_DATA_W_REG, quat_data, 8);

    quaternion_t q;
    esp_err_t ret = imu_read_quaternion(&q);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -0.5f, q.w);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, -1.0f / 16384.0f, q.x);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 1.0f / 16384.0f, q.y);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, q.z);
}

// ---------------------------------------------------------------------------
// Test: imu_read_euler converts raw int16 to radians correctly
// Format at reg 0x1A: yaw(2), roll(2), pitch(2) — scale 1/16 deg, then deg2rad
// ---------------------------------------------------------------------------
void test_imu_read_euler(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // yaw=2880 (180 deg), roll=1440 (90 deg), pitch=0
    // 2880 = 0x0B40, 1440 = 0x05A0
    uint8_t euler_data[6] = {
        0x40, 0x0B,  // yaw = 2880 raw → 180.0 deg → pi rad
        0xA0, 0x05,  // roll = 1440 raw → 90.0 deg → pi/2 rad
        0x00, 0x00,  // pitch = 0 → 0.0
    };
    mock_i2c_set_read_data(IMU_ADDR, BNO055_EUL_DATA_H_REG, euler_data, 6);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_EUL_DATA_H_REG, euler_data, 6);

    euler_t e;
    esp_err_t ret = imu_read_euler(&e);
    TEST_ASSERT_EQUAL(ESP_OK, ret);

    const float pi = 3.14159265f;
    TEST_ASSERT_FLOAT_WITHIN(0.01f, pi, e.yaw);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, pi / 2.0f, e.roll);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, e.pitch);
}

// ---------------------------------------------------------------------------
// Test: imu_read_angular_velocity converts raw int16 to rad/s
// Scale: 1/16 dps, then * pi/180 → rad/s
// ---------------------------------------------------------------------------
void test_imu_read_angular_velocity(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // x=160 (10 dps), y=0, z=-160 (-10 dps)
    // 160 = 0x00A0
    uint8_t gyro_data[6] = {
        0xA0, 0x00,  // x = 160 → 10 dps → 10 * pi/180 rad/s
        0x00, 0x00,  // y = 0
        0x60, 0xFF,  // z = -160 (0xFF60) → -10 dps → -10 * pi/180 rad/s
    };
    mock_i2c_set_read_data(IMU_ADDR, BNO055_GYR_DATA_X_REG, gyro_data, 6);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_GYR_DATA_X_REG, gyro_data, 6);

    vec3_t gyro;
    esp_err_t ret = imu_read_angular_velocity(&gyro);
    TEST_ASSERT_EQUAL(ESP_OK, ret);

    const float expected = 10.0f * 3.14159265f / 180.0f;
    TEST_ASSERT_FLOAT_WITHIN(0.01f, expected, gyro.x);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, gyro.y);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -expected, gyro.z);
}

// ---------------------------------------------------------------------------
// Test: imu_read_linear_accel converts raw int16 to m/s^2
// Scale: 1/100 m/s^2
// ---------------------------------------------------------------------------
void test_imu_read_linear_accel(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // x=981 (9.81 m/s^2), y=0, z=-100 (-1.0 m/s^2)
    // 981 = 0x03D5, -100 = 0xFF9C
    uint8_t accel_data[6] = {
        0xD5, 0x03,  // x = 981 → 9.81 m/s^2
        0x00, 0x00,  // y = 0
        0x9C, 0xFF,  // z = -100 → -1.0 m/s^2
    };
    mock_i2c_set_read_data(IMU_ADDR, BNO055_LIA_DATA_X_REG, accel_data, 6);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_LIA_DATA_X_REG, accel_data, 6);

    vec3_t accel;
    esp_err_t ret = imu_read_linear_accel(&accel);
    TEST_ASSERT_EQUAL(ESP_OK, ret);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 9.81f, accel.x);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, accel.y);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -1.0f, accel.z);
}

// ---------------------------------------------------------------------------
// Test: imu_is_calibrated returns true when register 0x35 == 0xFF
// ---------------------------------------------------------------------------
void test_imu_is_calibrated_true(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    uint8_t calib = 0xFF;
    mock_i2c_set_read_data(IMU_ADDR, BNO055_CALIB_STAT_REG, &calib, 1);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_CALIB_STAT_REG, &calib, 1);

    TEST_ASSERT_TRUE(imu_is_calibrated());
}

// ---------------------------------------------------------------------------
// Test: imu_is_calibrated returns false when register 0x35 != 0xFF
// ---------------------------------------------------------------------------
void test_imu_is_calibrated_false(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    uint8_t calib = 0x3F;  // Not fully calibrated
    mock_i2c_set_read_data(IMU_ADDR, BNO055_CALIB_STAT_REG, &calib, 1);
    mock_i2c_set_read_data(IMU_ADDR_ALT, BNO055_CALIB_STAT_REG, &calib, 1);

    TEST_ASSERT_FALSE(imu_is_calibrated());
}

// ---------------------------------------------------------------------------
// Test: imu_read_quaternion returns error on I2C failure
// ---------------------------------------------------------------------------
void test_imu_read_fails_i2c_error(void)
{
    mock_i2c_reset();
    setup_imu_init_success();
    imu_init();

    // Set read error for both possible addresses
    mock_i2c_set_read_error(IMU_ADDR, ESP_FAIL);
    mock_i2c_set_read_error(IMU_ADDR_ALT, ESP_FAIL);

    quaternion_t q;
    esp_err_t ret = imu_read_quaternion(&q);
    TEST_ASSERT_EQUAL(ESP_FAIL, ret);
}
