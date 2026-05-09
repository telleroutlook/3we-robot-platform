// SPDX-License-Identifier: Apache-2.0
#ifndef WIFI_PROVISION_H
#define WIFI_PROVISION_H

#include "esp_err.h"
#include <stddef.h>

#define WIFI_CRED_MAX_LEN 64

typedef struct {
    char ssid[WIFI_CRED_MAX_LEN];
    char password[WIFI_CRED_MAX_LEN];
} wifi_credentials_t;

esp_err_t wifi_provision_get_credentials(wifi_credentials_t *creds);
esp_err_t wifi_provision_store_credentials(const char *ssid, const char *password);
esp_err_t wifi_provision_start_sta(void);

#endif // WIFI_PROVISION_H
