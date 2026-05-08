// SPDX-License-Identifier: Apache-2.0
#include "motor_control.h"
#include "ultrasonic.h"
#include "encoder.h"
#include "imu.h"
#include "i2c_bus.h"
#include "battery.h"
#include "safety.h"
#include "microros_transport.h"
#include "dtls_transport.h"
#include "ota_signing.h"
#include "payload_hotplug.h"
#include "thermal_monitor.h"
#include "udp_transport.h"
#include "robot_params.h"
#include "pin_definitions.h"

#ifdef CONFIG_ROBOT_SKU_INDUSTRIAL
#include "canbus.h"
#endif

#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "main";

#define TASK_STACK_SAFETY    4096
#define TASK_STACK_SENSORS   3072
#define TASK_STACK_BATTERY   2048
#define TASK_STACK_MICROROS  16384
#define TASK_STACK_DTLS      8192
#define TASK_STACK_PAYLOAD   3072
#define TASK_STACK_THERMAL   2048
#define TASK_STACK_UDP       4096
#define TASK_STACK_CANBUS    3072

#define TASK_PRIO_SAFETY     (configMAX_PRIORITIES - 1)
#define TASK_PRIO_MICROROS   5
#define TASK_PRIO_SENSORS    4
#define TASK_PRIO_DTLS       4
#define TASK_PRIO_PAYLOAD    3
#define TASK_PRIO_THERMAL    3
#define TASK_PRIO_BATTERY    2
#define TASK_PRIO_UDP        3
#define TASK_PRIO_CANBUS     4

void app_main(void)
{
    ESP_LOGI(TAG, "Robot Platform Firmware starting...");

    // NVS (required for Wi-Fi, persistent config)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    // Safety first - must be operational before any motor activity
    ESP_ERROR_CHECK(safety_init());
    ESP_ERROR_CHECK(safety_relay_selftest());

    // Initialize motor subsystem
    ESP_ERROR_CHECK(motor_init());
    ESP_ERROR_CHECK(encoder_init());
    ESP_ERROR_CHECK(ultrasonic_init());

    // I2C bus mutex must be initialized before any I2C consumers
    ESP_ERROR_CHECK(i2c_bus_init());

    esp_err_t imu_ret = imu_init();
    if (imu_ret != ESP_OK) {
        ESP_LOGW(TAG, "IMU init failed (0x%x) - running without orientation fusion", imu_ret);
    }

    ESP_ERROR_CHECK(battery_init());

    // Thermal monitoring (INA219)
    esp_err_t thermal_ret = thermal_monitor_init();
    if (thermal_ret != ESP_OK) {
        ESP_LOGW(TAG, "Thermal monitor init failed - running without thermal protection");
    }

    // Payload hot-plug system
    ESP_ERROR_CHECK(payload_hotplug_init());

    // OTA signing: load public key from NVS
    nvs_handle_t nvs_ota;
    if (nvs_open("security", NVS_READONLY, &nvs_ota) == ESP_OK) {
        uint8_t ota_pubkey[OTA_PUBKEY_SIZE];
        size_t pubkey_len = OTA_PUBKEY_SIZE;
        if (nvs_get_blob(nvs_ota, "ota_pubkey", ota_pubkey, &pubkey_len) == ESP_OK) {
            ota_signing_init(ota_pubkey);
        } else {
            ESP_LOGW(TAG, "OTA pubkey not provisioned - OTA updates will be rejected");
        }
        nvs_close(nvs_ota);
    } else {
        ESP_LOGW(TAG, "Security NVS namespace not found - OTA disabled");
    }

    // Communication: micro-ROS over UART
    ESP_ERROR_CHECK(microros_init());

    // Communication: UDP fallback transport (telemetry only - no motor commands)
#ifndef CONFIG_ROBOT_ALLOW_PLAINTEXT_CTRL
    // UDP transport is restricted to read-only telemetry when DTLS is available
#endif
    udp_transport_config_t udp_cfg = {
        .cmd_port = UDP_CMD_PORT,
        .telemetry_port = UDP_TELEM_PORT,
        .timeout_ms = 1000,
    };
    esp_err_t udp_ret = udp_transport_init(&udp_cfg);
    if (udp_ret != ESP_OK) {
        ESP_LOGW(TAG, "UDP transport init failed - DTLS only mode");
    }

    // Communication: DTLS encrypted control channel
    dtls_config_t dtls_cfg = {
        .listen_port = 5684,
        .psk_identity = "robot-platform",
        .psk_key = {0},
        .psk_key_len = 16,
        .handshake_timeout_ms = 10000,
        .session_timeout_ms = 60000,
    };

    // Load PSK from NVS - refuse to start DTLS with unprovisioned key
    nvs_handle_t nvs_dtls;
    if (nvs_open("security", NVS_READONLY, &nvs_dtls) == ESP_OK) {
        size_t key_len = sizeof(dtls_cfg.psk_key);
        if (nvs_get_blob(nvs_dtls, "dtls_psk", dtls_cfg.psk_key, &key_len) == ESP_OK) {
            dtls_cfg.psk_key_len = (uint8_t)key_len;
        }
        nvs_close(nvs_dtls);
    }

    // Validate PSK is provisioned (not all-zeros)
    static const uint8_t zero_key[sizeof(dtls_cfg.psk_key)] = {0};
    esp_err_t dtls_ret;
    if (memcmp(dtls_cfg.psk_key, zero_key, sizeof(dtls_cfg.psk_key)) == 0) {
        ESP_LOGE(TAG, "DTLS PSK not provisioned - encrypted channel DISABLED. "
                 "Provision a key via NVS 'security/dtls_psk' before deployment.");
        dtls_ret = ESP_ERR_INVALID_STATE;
    } else {
        dtls_ret = dtls_init(&dtls_cfg);
        if (dtls_ret != ESP_OK) {
            ESP_LOGW(TAG, "DTLS init failed - encrypted channel unavailable");
        }
    }

#ifdef CONFIG_ROBOT_SKU_INDUSTRIAL
    // CAN bus (industrial SKU only)
    canbus_config_t can_cfg = {
        .spi_host = CAN_SPI_HOST,
        .pin_mosi = CAN_MOSI,
        .pin_miso = CAN_MISO,
        .pin_sclk = CAN_SCLK,
        .pin_cs = CAN_CS,
        .pin_int = CAN_INT,
        .bitrate = CAN_BITRATE_500K,
        .accept_mask = 0x7FF,
        .accept_filter = 0x000,
    };
    esp_err_t can_ret = canbus_init(&can_cfg);
    if (can_ret != ESP_OK) {
        ESP_LOGW(TAG, "CAN bus init failed");
    }
#endif

    // Create FreeRTOS tasks (highest priority first)
    xTaskCreate(safety_task, "safety", TASK_STACK_SAFETY, NULL, TASK_PRIO_SAFETY, NULL);
    xTaskCreate(microros_task, "microros", TASK_STACK_MICROROS, NULL, TASK_PRIO_MICROROS, NULL);
    xTaskCreate(ultrasonic_task, "ultrasonic", TASK_STACK_SENSORS, NULL, TASK_PRIO_SENSORS, NULL);
    xTaskCreate(payload_hotplug_task, "payload", TASK_STACK_PAYLOAD, NULL, TASK_PRIO_PAYLOAD, NULL);
    xTaskCreate(battery_task, "battery", TASK_STACK_BATTERY, NULL, TASK_PRIO_BATTERY, NULL);

    if (thermal_ret == ESP_OK) {
        xTaskCreate(thermal_monitor_task, "thermal", TASK_STACK_THERMAL, NULL, TASK_PRIO_THERMAL, NULL);
    }

    if (udp_ret == ESP_OK) {
        xTaskCreate(udp_transport_task, "udp_xport", TASK_STACK_UDP, NULL, TASK_PRIO_UDP, NULL);
    }

    if (dtls_ret == ESP_OK) {
        dtls_start();
        xTaskCreate(dtls_task, "dtls", TASK_STACK_DTLS, NULL, TASK_PRIO_DTLS, NULL);
    }

#ifdef CONFIG_ROBOT_SKU_INDUSTRIAL
    if (can_ret == ESP_OK) {
        xTaskCreate(canbus_task, "canbus", TASK_STACK_CANBUS, NULL, TASK_PRIO_CANBUS, NULL);
    }
#endif

    ESP_LOGI(TAG, "All systems initialized. Robot ready.");

    // Main loop: watchdog feed and status monitoring
    while (1) {
        safety_feed_watchdog();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
