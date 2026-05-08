// SPDX-License-Identifier: Apache-2.0
#ifndef MOCK_RMT_RX_H
#define MOCK_RMT_RX_H

#include <stdint.h>
#include <stddef.h>

typedef void *rmt_channel_handle_t;
typedef struct {
    uint32_t signal_range_min_ns;
    uint32_t signal_range_max_ns;
} rmt_receive_config_t;

typedef struct {
    uint16_t duration0;
    uint16_t level0;
    uint16_t duration1;
    uint16_t level1;
} rmt_symbol_word_t;

typedef struct {
    int gpio_num;
    int clk_src;
    uint32_t resolution_hz;
    size_t mem_block_symbols;
} rmt_rx_channel_config_t;

typedef struct {
    void (*on_recv_done)(rmt_channel_handle_t, void *, void *);
} rmt_rx_event_callbacks_t;

#define RMT_CLK_SRC_DEFAULT 0

static inline int rmt_new_rx_channel(const rmt_rx_channel_config_t *cfg, rmt_channel_handle_t *ch) {
    (void)cfg; *ch = (void*)0x1; return 0;
}
static inline int rmt_rx_register_event_callbacks(rmt_channel_handle_t ch, const rmt_rx_event_callbacks_t *cbs, void *ctx) {
    (void)ch; (void)cbs; (void)ctx; return 0;
}
static inline int rmt_enable(rmt_channel_handle_t ch) { (void)ch; return 0; }
static inline int rmt_receive(rmt_channel_handle_t ch, void *buf, size_t len, const rmt_receive_config_t *cfg) {
    (void)ch; (void)buf; (void)len; (void)cfg; return 0;
}

#endif
