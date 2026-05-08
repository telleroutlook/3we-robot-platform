// SPDX-License-Identifier: Apache-2.0
#include "motor_control.h"
#include "ultrasonic.h"
#include "encoder.h"
#include "imu.h"
#include "battery.h"
#include "safety.h"
#include "microros_transport.h"
#include "robot_params.h"

#include "esp_log.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "main";

#define TASK_STACK_SAFETY    2048
#define TASK_STACK_SENSORS   3072
#define TASK_STACK_BATTERY   2048
#define TASK_STACK_MICROROS  16384

#define TASK_PRIO_SAFETY     (configMAX_PRIORITIES - 1)
#define TASK_PRIO_MICROROS   5
#define TASK_PRIO_SENSORS    4
#define TASK_PRIO_BATTERY    2

void app_main(void)
{
    ESP_LOGI(TAG, "Robot Platform Firmware starting...");

    // NVS (required for Wi-Fi, persistent config)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    // Safety first - must be operational before any motor activity
    ESP_ERROR_CHECK(safety_init());

    // Initialize subsystems
    ESP_ERROR_CHECK(motor_init());
    ESP_ERROR_CHECK(encoder_init());
    ESP_ERROR_CHECK(ultrasonic_init());

    esp_err_t imu_ret = imu_init();
    if (imu_ret != ESP_OK) {
        ESP_LOGW(TAG, "IMU init failed (0x%x) - running without orientation fusion", imu_ret);
    }

    ESP_ERROR_CHECK(battery_init());
    ESP_ERROR_CHECK(microros_init());

    // Create FreeRTOS tasks
    xTaskCreate(safety_task, "safety", TASK_STACK_SAFETY, NULL, TASK_PRIO_SAFETY, NULL);
    xTaskCreate(ultrasonic_task, "ultrasonic", TASK_STACK_SENSORS, NULL, TASK_PRIO_SENSORS, NULL);
    xTaskCreate(battery_task, "battery", TASK_STACK_BATTERY, NULL, TASK_PRIO_BATTERY, NULL);
    xTaskCreate(microros_task, "microros", TASK_STACK_MICROROS, NULL, TASK_PRIO_MICROROS, NULL);

    ESP_LOGI(TAG, "All systems initialized. Robot ready.");

    // Main loop: watchdog feed and status monitoring
    while (1) {
        if (!safety_is_estopped()) {
            safety_feed_watchdog();
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
