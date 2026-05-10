// SPDX-License-Identifier: Apache-2.0
#ifndef ADC_MANAGER_H
#define ADC_MANAGER_H

#include "esp_err.h"
#include "esp_adc/adc_oneshot.h"

esp_err_t adc_manager_init(void);
adc_oneshot_unit_handle_t adc_manager_get_handle(void);

#endif // ADC_MANAGER_H
