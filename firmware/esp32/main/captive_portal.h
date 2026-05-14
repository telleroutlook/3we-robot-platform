// SPDX-License-Identifier: Apache-2.0
#ifndef CAPTIVE_PORTAL_H
#define CAPTIVE_PORTAL_H

#include "esp_err.h"
#include "esp_http_server.h"
#include "esp_https_server.h"

#include <stdbool.h>

typedef void (*captive_portal_done_cb_t)(const char *ssid, const char *password);

typedef struct {
    captive_portal_done_cb_t on_credentials_received;
    uint16_t http_port;
    uint8_t wifi_channel;
} captive_portal_config_t;

#define CAPTIVE_PORTAL_DEFAULT_CONFIG() { \
    .on_credentials_received = NULL,      \
    .http_port = 80,                      \
    .wifi_channel = 6,                    \
}

esp_err_t captive_portal_start(const captive_portal_config_t *config);
esp_err_t captive_portal_stop(void);
bool captive_portal_is_active(void);
httpd_handle_t captive_portal_get_httpd(void);

#endif // CAPTIVE_PORTAL_H
