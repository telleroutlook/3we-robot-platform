// SPDX-License-Identifier: Apache-2.0
#ifndef CANBUS_H
#define CANBUS_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

#define CAN_BITRATE_125K    125000
#define CAN_BITRATE_250K    250000
#define CAN_BITRATE_500K    500000
#define CAN_BITRATE_1M      1000000

#define CAN_MAX_DATA_LEN    8

typedef struct {
    uint32_t id;
    bool extended;
    bool rtr;
    uint8_t dlc;
    uint8_t data[CAN_MAX_DATA_LEN];
} can_frame_t;

typedef void (*can_recv_callback_t)(const can_frame_t *frame);

typedef struct {
    uint8_t spi_host;       // SPI2_HOST or SPI3_HOST
    uint8_t pin_mosi;
    uint8_t pin_miso;
    uint8_t pin_sclk;
    uint8_t pin_cs;
    uint8_t pin_int;
    uint32_t bitrate;
    uint32_t accept_mask;
    uint32_t accept_filter;
} canbus_config_t;

esp_err_t canbus_init(const canbus_config_t *config);
esp_err_t canbus_send(const can_frame_t *frame);
void canbus_set_recv_callback(can_recv_callback_t cb);
esp_err_t canbus_set_filter(uint32_t mask, uint32_t filter);
esp_err_t canbus_set_bitrate(uint32_t bitrate);
bool canbus_is_ready(void);
void canbus_task(void *params);

#endif // CANBUS_H
