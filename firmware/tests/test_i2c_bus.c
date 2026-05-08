// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "i2c_bus.h"

void test_i2c_bus_init_success(void)
{
    esp_err_t err = i2c_bus_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

void test_i2c_bus_init_idempotent(void)
{
    esp_err_t err1 = i2c_bus_init();
    esp_err_t err2 = i2c_bus_init();
    TEST_ASSERT_EQUAL(ESP_OK, err1);
    TEST_ASSERT_EQUAL(ESP_OK, err2);
}

void test_i2c_bus_get_mutex_after_init(void)
{
    i2c_bus_init();
    SemaphoreHandle_t mtx = i2c_bus_get_mutex();
    TEST_ASSERT_TRUE(mtx != NULL);
}

void test_i2c_bus_lock_unlock_cycle(void)
{
    i2c_bus_init();
    bool locked = i2c_bus_lock();
    TEST_ASSERT_TRUE(locked);
    i2c_bus_unlock();
}
