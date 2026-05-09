// SPDX-License-Identifier: Apache-2.0
#ifndef OTA_UPDATE_H
#define OTA_UPDATE_H

#include "esp_err.h"
#include "esp_http_server.h"

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    OTA_STATUS_IDLE = 0,
    OTA_STATUS_DOWNLOADING,
    OTA_STATUS_VERIFYING,
    OTA_STATUS_APPLYING,
    OTA_STATUS_REBOOTING,
    OTA_STATUS_FAILED
} ota_status_t;

typedef struct {
    ota_status_t status;
    uint8_t progress_pct;
    uint32_t bytes_received;
    uint32_t bytes_total;
    char error_msg[64];
} ota_progress_t;

esp_err_t ota_update_init(httpd_handle_t httpd);
esp_err_t ota_update_start_from_url(const char *url);
ota_progress_t ota_update_get_progress(void);
void ota_update_task(void *params);

#endif // OTA_UPDATE_H
