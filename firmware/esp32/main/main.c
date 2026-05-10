// SPDX-License-Identifier: Apache-2.0
#include "motor_control.h"
#include "ultrasonic.h"
#include "encoder.h"
#include "imu.h"
#include "i2c_bus.h"
#include "battery.h"
#include "safety.h"
#ifndef MICROROS_DISABLED
#include "microros_transport.h"
#endif
#include "dtls_transport.h"
#include "ota_signing.h"
#include "ota_update.h"
#include "ota_preflight.h"
#include "payload_hotplug.h"
#include "thermal_monitor.h"
#include "udp_transport.h"
#include "wifi_provision.h"
#include "captive_portal.h"
#include "heartbeat_monitor.h"
#include "external_wdt.h"
#include "adc_manager.h"
#include "robot_params.h"
#include "pin_definitions.h"

#ifdef CONFIG_ROBOT_SKU_INDUSTRIAL
#include "canbus.h"
#endif

#include "esp_log.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include <string.h>
#include <stdio.h>

static const char *TAG = "main";

#define TASK_STACK_SAFETY    4096
#define TASK_STACK_SENSORS   3072
#define TASK_STACK_BATTERY   2048
#define TASK_STACK_MICROROS  16384
#define TASK_STACK_DTLS      12288
#define TASK_STACK_PAYLOAD   3072
#define TASK_STACK_THERMAL   2048
#define TASK_STACK_UDP       4096
#define TASK_STACK_CANBUS    3072
#define TASK_STACK_OTA       8192
#define TASK_STACK_HEARTBEAT 2048
#define TASK_STACK_EXT_WDT   1024

#define TASK_PRIO_SAFETY     (configMAX_PRIORITIES - 1)
#define TASK_PRIO_MICROROS   5
#define TASK_PRIO_SENSORS    4
#define TASK_PRIO_DTLS       4
#define TASK_PRIO_PAYLOAD    3
#define TASK_PRIO_THERMAL    3
#define TASK_PRIO_BATTERY    2
#define TASK_PRIO_UDP        3
#define TASK_PRIO_CANBUS     4
#define TASK_PRIO_OTA        2
#define TASK_PRIO_HEARTBEAT  (configMAX_PRIORITIES - 2)
#define TASK_PRIO_EXT_WDT    (configMAX_PRIORITIES - 1)

#define WIFI_CONNECT_TIMEOUT_MS  10000

static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void captive_portal_done(const char *ssid, const char *password)
{
    ESP_LOGI(TAG, "Credentials received via captive portal, restarting...");
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
}

void app_main(void)
{
    ESP_LOGI(TAG, "Robot Platform Firmware starting...");

    // NVS (required for Wi-Fi, persistent config)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    // Network: initialize event loop and try Wi-Fi STA, fall back to captive portal
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(esp_netif_init());
    s_wifi_event_group = xEventGroupCreate();

    wifi_credentials_t wifi_creds;
    bool wifi_connected = false;
    if (wifi_provision_get_credentials(&wifi_creds) == ESP_OK) {
        esp_netif_create_default_wifi_sta();
        esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
        esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL);

        wifi_provision_start_sta();

        EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE, pdFALSE, pdMS_TO_TICKS(WIFI_CONNECT_TIMEOUT_MS));

        if (bits & WIFI_CONNECTED_BIT) {
            ESP_LOGI(TAG, "Wi-Fi connected");
            wifi_connected = true;
        } else {
            ESP_LOGW(TAG, "Wi-Fi connection failed - starting captive portal");
            esp_wifi_stop();
        }
    }

    if (!wifi_connected) {
        captive_portal_config_t portal_cfg = CAPTIVE_PORTAL_DEFAULT_CONFIG();
        portal_cfg.on_credentials_received = captive_portal_done;
        captive_portal_start(&portal_cfg);
    }

    // Safety first - must be operational before any motor activity
    ESP_ERROR_CHECK(safety_init());
    ESP_ERROR_CHECK(safety_relay_selftest());

    if (safety_get_state() == SAFETY_RELAY_FAULT) {
        ESP_LOGE(TAG, "SAFETY HALT: relay fault persisted - requires physical service");
        while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }

    // OTA rollback: track pending verification state for delayed validation
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;
    bool ota_pending_verify = false;
    if (esp_ota_get_state_partition(running, &ota_state) == ESP_OK) {
        if (ota_state == ESP_OTA_IMG_PENDING_VERIFY) {
            ota_pending_verify = true;
            ota_preflight_increment_boot_fail();
            uint8_t fails = ota_preflight_get_boot_fail_count();
            if (fails >= OTA_PREFLIGHT_MAX_BOOT_FAILURES) {
                ESP_LOGE(TAG, "OTA: %d consecutive boot failures - NOT confirming firmware", fails);
                // Watchdog will reset and bootloader will revert to previous partition
            } else {
                ESP_LOGI(TAG, "OTA: pending verify (attempt %d/%d) - will confirm after 30s validation",
                         fails, OTA_PREFLIGHT_MAX_BOOT_FAILURES);
            }
        }
    }

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

    ESP_ERROR_CHECK(adc_manager_init());
    ESP_ERROR_CHECK(battery_init());

    // Heartbeat monitor (Pi 5 power watchdog)
    ESP_ERROR_CHECK(heartbeat_monitor_init());

    // External hardware watchdog (TPS3813 toggle feed)
    ESP_ERROR_CHECK(external_wdt_init());

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
#ifndef MICROROS_DISABLED
    ESP_ERROR_CHECK(microros_init());
#endif

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
        .psk_identity = {0},
        .psk_key = {0},
        .psk_key_len = 16,
        .handshake_timeout_ms = 10000,
        .session_timeout_ms = 60000,
        .max_sessions = DTLS_MAX_SESSIONS,
        .authority_idle_timeout_ms = DTLS_AUTHORITY_IDLE_MS,
    };

    // Derive PSK identity from device MAC for per-unit isolation
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    snprintf(dtls_cfg.psk_identity, sizeof(dtls_cfg.psk_identity),
             "robot-%02X%02X%02X%02X%02X%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // Load PSK from NVS - refuse to start DTLS with unprovisioned key
    nvs_handle_t nvs_dtls;
    if (nvs_open("security", NVS_READONLY, &nvs_dtls) == ESP_OK) {
        size_t key_len = sizeof(dtls_cfg.psk_key);
        if (nvs_get_blob(nvs_dtls, "dtls_psk", dtls_cfg.psk_key, &key_len) == ESP_OK) {
            dtls_cfg.psk_key_len = (uint8_t)key_len;
        }
        nvs_close(nvs_dtls);
    }

    // Validate PSK is provisioned (not all-zeros or too short)
    static const uint8_t zero_key[sizeof(dtls_cfg.psk_key)] = {0};
    esp_err_t dtls_ret;
    if (dtls_cfg.psk_key_len < 16 ||
        memcmp(dtls_cfg.psk_key, zero_key, dtls_cfg.psk_key_len) == 0) {
        ESP_LOGE(TAG, "DTLS PSK not provisioned - encrypted channel DISABLED. "
                 "Provision a key via NVS 'security/dtls_psk' before deployment.");
        dtls_ret = ESP_ERR_INVALID_STATE;
    } else {
        dtls_ret = dtls_init(&dtls_cfg);
        if (dtls_ret != ESP_OK) {
            ESP_LOGW(TAG, "DTLS init failed - encrypted channel unavailable");
        } else {
            dtls_load_operators_from_nvs();
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
    BaseType_t rc;
    rc = xTaskCreate(safety_task, "safety", TASK_STACK_SAFETY, NULL, TASK_PRIO_SAFETY, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: safety_task creation failed - rebooting");
        esp_restart();
    }
#ifndef MICROROS_DISABLED
    rc = xTaskCreate(microros_task, "microros", TASK_STACK_MICROROS, NULL, TASK_PRIO_MICROROS, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: microros_task creation failed - rebooting");
        esp_restart();
    }
#endif
    rc = xTaskCreate(ultrasonic_task, "ultrasonic", TASK_STACK_SENSORS, NULL, TASK_PRIO_SENSORS, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: ultrasonic_task creation failed - rebooting");
        esp_restart();
    }
    rc = xTaskCreate(payload_hotplug_task, "payload", TASK_STACK_PAYLOAD, NULL, TASK_PRIO_PAYLOAD, NULL);
    if (rc != pdPASS) {
        ESP_LOGW(TAG, "payload_hotplug_task creation failed");
    }
    rc = xTaskCreate(battery_task, "battery", TASK_STACK_BATTERY, NULL, TASK_PRIO_BATTERY, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: battery_task creation failed - rebooting");
        esp_restart();
    }

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

    // OTA update task
    ota_update_init(captive_portal_get_httpd());
    xTaskCreate(ota_update_task, "ota", TASK_STACK_OTA, NULL, TASK_PRIO_OTA, NULL);

    // Heartbeat monitor task (watches Pi 5 liveness)
    rc = xTaskCreate(heartbeat_monitor_task, "heartbeat", TASK_STACK_HEARTBEAT, NULL, TASK_PRIO_HEARTBEAT, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: heartbeat_monitor_task creation failed - rebooting");
        esp_restart();
    }

    // External watchdog feed task (highest priority — must never starve)
    rc = xTaskCreate(external_wdt_task, "ext_wdt", TASK_STACK_EXT_WDT, NULL, TASK_PRIO_EXT_WDT, NULL);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: external_wdt_task creation failed - rebooting");
        esp_restart();
    }

    ESP_LOGI(TAG, "All systems initialized. Robot ready.");

    // Main loop: OTA delayed validation + status monitoring
    uint32_t uptime_ms = 0;
    bool ota_confirmed = false;
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(100));
        uptime_ms += 100;

        // 30-second delayed OTA validation window
        if (ota_pending_verify && !ota_confirmed &&
            uptime_ms >= OTA_PREFLIGHT_VALIDATION_TIMEOUT_MS) {
            uint8_t fails = ota_preflight_get_boot_fail_count();
            if (fails < OTA_PREFLIGHT_MAX_BOOT_FAILURES &&
                safety_get_state() == SAFETY_NORMAL &&
                motor_is_stopped()) {
                ESP_LOGI(TAG, "OTA: 30s validation passed - confirming new firmware");
                esp_ota_mark_app_valid_cancel_rollback();
                ota_preflight_clear_boot_fail();
                ota_confirmed = true;
            }
        }
    }
}
