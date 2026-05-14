# SPDX-License-Identifier: Apache-2.0

set(SRCS
    "main.c"
    "motor_control.c"
    "ultrasonic.c"
    "encoder.c"
    "imu.c"
    "i2c_bus.c"
    "battery.c"
    "safety.c"
    "dtls_transport.c"
    "dtls_authority.c"
    "ota_signing.c"
    "ota_update.c"
    "ota_preflight.c"
    "ota_compat.c"
    "payload_hotplug.c"
    "payload_power.c"
    "canbus.c"
    "thermal_monitor.c"
    "udp_transport.c"
    "wifi_provision.c"
    "captive_portal.c"
    "heartbeat_monitor.c"
    "external_wdt.c"
    "adc_manager.c"
)

set(PRIV_REQS "")
set(COMPILE_DEFS "")

if(CONFIG_ROBOT_DOCKING_ENABLED)
    list(APPEND SRCS "charging_detect.c")
endif()

if(CONFIG_CURRENT_SENSE_ENABLED)
    list(APPEND SRCS "current_sense.c")
endif()

if(CONFIG_ROBOT_BASIC_STANDALONE OR DEFINED ENV{CI})
    list(APPEND COMPILE_DEFS "MICROROS_DISABLED=1")
else()
    list(APPEND SRCS "microros_transport.c")
    set(PRIV_REQS micro_ros_espidf_component)
endif()

idf_component_register(
    SRCS ${SRCS}
    INCLUDE_DIRS
        "."
        "../../config"
    REQUIRES
        driver
        esp_timer
        esp_adc
        nvs_flash
        esp_event
        esp_wifi
        esp_netif
        esp_http_server
        esp_https_server
        esp_http_client
        esp-tls
        lwip
        mbedtls
        app_update
        esp_partition
        json
    PRIV_REQUIRES
        ${PRIV_REQS}
    EMBED_FILES
        "certs/captive_portal_cert.pem"
        "certs/captive_portal_key.pem"
)

if(COMPILE_DEFS)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ${COMPILE_DEFS})
endif()
