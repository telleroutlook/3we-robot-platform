// SPDX-License-Identifier: Apache-2.0
#ifndef MOCK_ESP_WIFI_H
#define MOCK_ESP_WIFI_H

#include <stdint.h>

typedef struct {
    uint8_t ssid[33];
    int8_t rssi;
    uint8_t channel;
} wifi_ap_record_t;

int esp_wifi_sta_get_ap_info(wifi_ap_record_t *ap_info);
void mock_set_wifi_rssi(int8_t rssi);
void mock_set_wifi_connected(int connected);

#endif // MOCK_ESP_WIFI_H
