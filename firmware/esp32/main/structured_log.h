// SPDX-License-Identifier: Apache-2.0
#ifndef STRUCTURED_LOG_H
#define STRUCTURED_LOG_H

#include "esp_log.h"
#include "sdkconfig.h"

#ifdef CONFIG_STRUCTURED_LOGGING

/**
 * Structured logging in logfmt format for machine-parseable output.
 * Output: ts=<uptime_ms> level=<L> tag=<T> event=<E> key1=val1 key2=val2 ...
 *
 * Usage:
 *   SLOG_I(TAG, "wifi_connected", "ssid=%s rssi=%d", ssid, rssi);
 *   SLOG_W(TAG, "battery_low", "pct=%d voltage_mv=%d", pct, mv);
 *   SLOG_E(TAG, "ota_failed", "reason=%s code=%d", reason, code);
 */

void slog_output(const char *level, const char *tag, const char *event,
                 const char *fmt, ...) __attribute__((format(printf, 4, 5)));

#define SLOG_I(tag, event, fmt, ...) \
    slog_output("I", tag, event, fmt, ##__VA_ARGS__)

#define SLOG_W(tag, event, fmt, ...) \
    slog_output("W", tag, event, fmt, ##__VA_ARGS__)

#define SLOG_E(tag, event, fmt, ...) \
    slog_output("E", tag, event, fmt, ##__VA_ARGS__)

#define SLOG_D(tag, event, fmt, ...) \
    slog_output("D", tag, event, fmt, ##__VA_ARGS__)

#else /* !CONFIG_STRUCTURED_LOGGING */

#define SLOG_I(tag, event, fmt, ...) ESP_LOGI(tag, "[%s] " fmt, event, ##__VA_ARGS__)
#define SLOG_W(tag, event, fmt, ...) ESP_LOGW(tag, "[%s] " fmt, event, ##__VA_ARGS__)
#define SLOG_E(tag, event, fmt, ...) ESP_LOGE(tag, "[%s] " fmt, event, ##__VA_ARGS__)
#define SLOG_D(tag, event, fmt, ...) ESP_LOGD(tag, "[%s] " fmt, event, ##__VA_ARGS__)

#endif /* CONFIG_STRUCTURED_LOGGING */

#endif /* STRUCTURED_LOG_H */
