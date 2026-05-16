// SPDX-License-Identifier: Apache-2.0
#ifndef EXTERNAL_WDT_H
#define EXTERNAL_WDT_H

#include "esp_err.h"

#define EXT_WDT_FEED_PERIOD_MS  200  // Toggle every 200ms (8× margin vs 1.6s TPS3813 timeout)
#define EXT_WDT_BOOT_GRACE_MS  30000  // Unconditional feeding during startup (covers WiFi + all init)

esp_err_t external_wdt_init(void);
void external_wdt_task(void *params);
void external_wdt_confirm_alive(void);

#endif // EXTERNAL_WDT_H
