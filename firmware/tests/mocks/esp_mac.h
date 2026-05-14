// SPDX-License-Identifier: Apache-2.0
// Shim: redirect to unified stubs
#ifndef ESP_MAC_H_MOCK
#define ESP_MAC_H_MOCK

#include "esp_stubs.h"
#include <string.h>

static inline esp_err_t esp_efuse_mac_get_default(uint8_t *mac)
{
    memset(mac, 0xAA, 6);
    return ESP_OK;
}

#endif
