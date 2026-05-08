// SPDX-License-Identifier: Apache-2.0
#ifndef MOCK_RMT_TX_H
#define MOCK_RMT_TX_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    int gpio_num;
    int clk_src;
    uint32_t resolution_hz;
    size_t mem_block_symbols;
} rmt_tx_channel_config_t;

typedef struct {
    uint32_t loop_count;
} rmt_transmit_config_t;

typedef void *rmt_encoder_handle_t;

typedef struct {
    uint32_t resolution;
} rmt_copy_encoder_config_t;

static inline int rmt_new_tx_channel(const rmt_tx_channel_config_t *cfg, void **ch) {
    (void)cfg; *ch = (void*)0x2; return 0;
}
static inline int rmt_new_copy_encoder(const rmt_copy_encoder_config_t *cfg, rmt_encoder_handle_t *enc) {
    (void)cfg; *enc = (void*)0x3; return 0;
}
static inline int rmt_transmit(void *ch, rmt_encoder_handle_t enc, const void *data, size_t len, const rmt_transmit_config_t *cfg) {
    (void)ch; (void)enc; (void)data; (void)len; (void)cfg; return 0;
}

#endif
