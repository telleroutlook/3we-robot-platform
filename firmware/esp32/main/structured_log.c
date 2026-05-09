// SPDX-License-Identifier: Apache-2.0
#include "structured_log.h"

#ifdef CONFIG_STRUCTURED_LOGGING

#include "esp_timer.h"

#include <stdarg.h>
#include <stdio.h>

void slog_output(const char *level, const char *tag, const char *event,
                 const char *fmt, ...)
{
    uint32_t ts_ms = (uint32_t)(esp_timer_get_time() / 1000);

    printf("ts=%lu level=%s tag=%s event=%s ", (unsigned long)ts_ms, level, tag, event);

    if (fmt && fmt[0] != '\0') {
        va_list args;
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
    }

    printf("\n");
}

#endif /* CONFIG_STRUCTURED_LOGGING */
