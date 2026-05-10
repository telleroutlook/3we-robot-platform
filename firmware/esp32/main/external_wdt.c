// SPDX-License-Identifier: Apache-2.0
#include "external_wdt.h"
#include "pin_definitions.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "ext_wdt";
static int s_wdt_level = 0;

esp_err_t external_wdt_init(void)
{
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << EXT_WDT_FEED_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_cfg);
    if (err != ESP_OK) return err;

    gpio_set_level(EXT_WDT_FEED_GPIO, 0);
    s_wdt_level = 0;

    ESP_LOGI(TAG, "External watchdog initialized (feed period=%dms)", EXT_WDT_FEED_PERIOD_MS);
    return ESP_OK;
}

void external_wdt_task(void *params)
{
    (void)params;

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(EXT_WDT_FEED_PERIOD_MS));
        s_wdt_level = !s_wdt_level;
        gpio_set_level(EXT_WDT_FEED_GPIO, s_wdt_level);
    }
}
