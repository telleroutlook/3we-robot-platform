// SPDX-License-Identifier: Apache-2.0
#ifndef CHARGING_DETECT_H
#define CHARGING_DETECT_H

#include "esp_err.h"
#include <stdbool.h>

#define CHARGE_CONTACT_THRESHOLD_MV  2000  // 2.0V = contact detected

esp_err_t charging_detect_init(void);
int charging_detect_get_voltage_mv(void);
bool charging_detect_is_connected(void);

#endif // CHARGING_DETECT_H
