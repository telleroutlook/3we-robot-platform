// SPDX-License-Identifier: Apache-2.0
#ifndef CHARGING_DETECT_H
#define CHARGING_DETECT_H

#include "esp_err.h"
#include <stdbool.h>

#define CHARGE_CONTACT_THRESHOLD_MV  2000  // 2.0V = contact detected (rising)
#define CHARGE_CONTACT_RELEASE_MV   1700  // 1.7V = contact lost (falling, hysteresis)

typedef enum {
    CHARGE_DETECT_NONE = 0,
    CHARGE_DETECT_ANALOG,
    CHARGE_DETECT_DIGITAL,
    CHARGE_DETECT_BOTH,
} charge_detect_method_t;

esp_err_t charging_detect_init(void);
int charging_detect_get_voltage_mv(void);
bool charging_detect_is_connected(void);
charge_detect_method_t charging_detect_get_method(void);

#endif // CHARGING_DETECT_H
