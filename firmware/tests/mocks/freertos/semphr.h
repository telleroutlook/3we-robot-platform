// SPDX-License-Identifier: Apache-2.0
#ifndef MOCK_FREERTOS_SEMPHR_H
#define MOCK_FREERTOS_SEMPHR_H

#include "freertos/FreeRTOS.h"

typedef void *SemaphoreHandle_t;

#define xSemaphoreCreateBinary()        ((SemaphoreHandle_t)0x1)
#define xSemaphoreCreateMutex()         ((SemaphoreHandle_t)0x2)
#define xSemaphoreTake(s, t)            (1)
#define xSemaphoreGive(s)               (1)
#define xSemaphoreGiveFromISR(s, w)     (1)

#endif
