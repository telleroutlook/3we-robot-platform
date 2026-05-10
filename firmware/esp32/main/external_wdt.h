// SPDX-License-Identifier: Apache-2.0
#ifndef EXTERNAL_WDT_H
#define EXTERNAL_WDT_H

#include "esp_err.h"

#define EXT_WDT_FEED_PERIOD_MS  500  // Toggle every 500ms (1Hz square wave)

esp_err_t external_wdt_init(void);
void external_wdt_task(void *params);

#endif // EXTERNAL_WDT_H
