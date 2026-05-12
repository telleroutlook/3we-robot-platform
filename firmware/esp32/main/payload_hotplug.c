// SPDX-License-Identifier: Apache-2.0
#include "payload_hotplug.h"
#include "i2c_bus.h"
#include "pin_definitions.h"

#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

static const char *TAG = "hotplug";

#define EEPROM_ADDR         0x50
#define EEPROM_ID_SCL       30  // PBC-34 pin 30 (mapped via MCP23017)
#define EEPROM_ID_SDA       31  // PBC-34 pin 31
#define DESCRIPTOR_MAGIC    "PBC4"
#define DEBOUNCE_MS         10
#define POWER_RAMP_MS       10
#define INIT_WAIT_MS        110
#define READY_CONFIRM_MS    100

// Capability bit definitions — aligned with sdk/payload_interface/capability_flags.py
#define CAP_I2C     (1 << 0)  // 0x01
#define CAP_SPI     (1 << 1)  // 0x02
#define CAP_UART    (1 << 2)  // 0x04
#define CAP_GPIO    (1 << 3)  // 0x08
#define CAP_ADC     (1 << 4)  // 0x10
#define CAP_PWM     (1 << 5)  // 0x20
#define CAP_CAN     (1 << 6)  // 0x40
#define CAP_CAMERA  (1 << 7)  // 0x80
#define ALLOWED_CAPABILITIES 0xFF
#define ALLOWED_GPIO_MASK    0x0F

// MCP23017 register addresses for payload power control
#define MCP_IODIRA          0x00
#define MCP_GPIOA           0x12
#define MCP_OLATA           0x14

static payload_state_t state = PAYLOAD_STATE_ABSENT;
static payload_descriptor_t descriptor;
static payload_event_callback_t event_callback = NULL;
static bool detect_pin_low = false;

static esp_err_t payload_mcp_write_bit(uint8_t bit, bool value)
{
    return mcp23017_write_bit(MCP23017_ADDR, MCP_OLATA, bit, value);
}

static bool read_detect_pin(void)
{
    uint8_t reg_val = 0;
    esp_err_t err = mcp23017_read_register(MCP23017_ADDR, MCP_GPIOA, &reg_val);
    if (err != ESP_OK) return false;
    return !(reg_val & (1 << PAYLOAD_DETECT_BIT));  // Active low
}

static esp_err_t read_eeprom_descriptor(payload_descriptor_t *desc)
{
    uint8_t data[64];
    uint8_t reg = 0x00;

    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;
    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, EEPROM_ADDR,
                                                  &reg, 1, data, 64, pdMS_TO_TICKS(100));
    i2c_bus_unlock();
    if (err != ESP_OK) return err;

    // Verify magic
    if (memcmp(data, DESCRIPTOR_MAGIC, 4) != 0) {
        ESP_LOGW(TAG, "Invalid EEPROM magic");
        return ESP_ERR_INVALID_RESPONSE;
    }

    // Parse descriptor
    memset(desc, 0, sizeof(*desc));
    memcpy(desc->payload_id, &data[5], 16);
    desc->payload_id[16] = '\0';
    memcpy(desc->name, &data[0x15], 32);
    desc->name[32] = '\0';
    desc->power_5v_ma = (data[0x35] << 8) | data[0x36];
    desc->power_12v_ma = (data[0x37] << 8) | data[0x38];
    desc->capabilities = data[0x39];
    desc->gpio_mask = data[0x3A];

    // Validate capabilities against hardware allowlist
    if (desc->capabilities & ~ALLOWED_CAPABILITIES) {
        ESP_LOGW(TAG, "Unsupported capabilities bits 0x%02X masked",
                 desc->capabilities & ~ALLOWED_CAPABILITIES);
        desc->capabilities &= ALLOWED_CAPABILITIES;
    }
    if (desc->gpio_mask & ~ALLOWED_GPIO_MASK) {
        ESP_LOGW(TAG, "GPIO mask 0x%02X exceeds allowed pins, masked to 0x%02X",
                 desc->gpio_mask, desc->gpio_mask & ALLOWED_GPIO_MASK);
        desc->gpio_mask &= ALLOWED_GPIO_MASK;
    }

    return ESP_OK;
}

static void notify_event(void)
{
    if (event_callback) event_callback(state, &descriptor);
}

static bool verify_power_budget(const payload_descriptor_t *desc)
{
    // 5V rail: 5000mA max
    if (desc->power_5v_ma > 5000) return false;
    // 12V rail: 3000mA max
    if (desc->power_12v_ma > 3000) return false;
    return true;
}

esp_err_t payload_hotplug_init(void)
{
    // Configure MCP23017 GPA0-2 as outputs (power control)
    // GPA3 as input (DETECT)
    uint8_t iodir_buf[2] = { MCP_IODIRA, 0xF8 };  // GPA0-2 output, GPA3-7 input
    if (!i2c_bus_lock()) return ESP_ERR_TIMEOUT;

    esp_err_t err = i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, iodir_buf, 2, pdMS_TO_TICKS(50));
    if (err != ESP_OK) {
        i2c_bus_unlock();
        ESP_LOGE(TAG, "MCP23017 IODIR write failed: 0x%x", err);
        return err;
    }

    // Ensure all power rails off at init
    uint8_t latch_buf[2] = { MCP_OLATA, 0x00 };
    err = i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, latch_buf, 2, pdMS_TO_TICKS(50));
    i2c_bus_unlock();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "MCP23017 OLAT write failed: 0x%x", err);
        return err;
    }

    state = PAYLOAD_STATE_ABSENT;
    ESP_LOGI(TAG, "Payload hot-plug system initialized");
    return ESP_OK;
}

payload_state_t payload_get_state(void)
{
    return state;
}

const payload_descriptor_t *payload_get_descriptor(void)
{
    if (state >= PAYLOAD_STATE_READY) return &descriptor;
    return NULL;
}

void payload_register_callback(payload_event_callback_t cb)
{
    event_callback = cb;
}

esp_err_t payload_power_off(void)
{
    payload_mcp_write_bit(PAYLOAD_VBAT_EN_BIT, false);
    payload_mcp_write_bit(PAYLOAD_12V_EN_BIT, false);
    payload_mcp_write_bit(PAYLOAD_5V_EN_BIT, false);

    state = PAYLOAD_STATE_ABSENT;
    notify_event();
    ESP_LOGI(TAG, "Payload power disabled");
    return ESP_OK;
}

void payload_hotplug_task(void *params)
{
    while (1) {
        switch (state) {
        case PAYLOAD_STATE_ABSENT:
            // T+0ms: Check DETECT pin
            if (read_detect_pin()) {
                state = PAYLOAD_STATE_DETECTED;
                ESP_LOGI(TAG, "Payload insertion detected");
            }
            break;

        case PAYLOAD_STATE_DETECTED:
            // T+10ms: Debounce confirmation
            vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));
            if (!read_detect_pin()) {
                state = PAYLOAD_STATE_ABSENT;
                break;
            }
            state = PAYLOAD_STATE_IDENTIFYING;
            break;

        case PAYLOAD_STATE_IDENTIFYING:
            // T+20ms: Read EEPROM descriptor
            if (read_eeprom_descriptor(&descriptor) == ESP_OK) {
                ESP_LOGI(TAG, "Identified: %s (ID: %s)", descriptor.name, descriptor.payload_id);

                // T+30ms: Verify power budget
                if (!verify_power_budget(&descriptor)) {
                    ESP_LOGE(TAG, "Power budget exceeded (5V:%dmA, 12V:%dmA)",
                             descriptor.power_5v_ma, descriptor.power_12v_ma);
                    state = PAYLOAD_STATE_FAULT;
                    notify_event();
                    break;
                }
                state = PAYLOAD_STATE_POWERING;
            } else {
                ESP_LOGW(TAG, "EEPROM read failed - no valid descriptor");
                state = PAYLOAD_STATE_FAULT;
                notify_event();
            }
            break;

        case PAYLOAD_STATE_POWERING:
            // T+40ms: Enable 3.3V ref (always on via hardware, no software control)
            // T+50ms: Enable 5V with soft-start ramp
            payload_mcp_write_bit(PAYLOAD_5V_EN_BIT, true);
            vTaskDelay(pdMS_TO_TICKS(POWER_RAMP_MS + 10));

            // T+70ms: Enable 12V if requested
            if (descriptor.power_12v_ma > 0) {
                payload_mcp_write_bit(PAYLOAD_12V_EN_BIT, true);
                vTaskDelay(pdMS_TO_TICKS(POWER_RAMP_MS + 10));
            }

            // T+90ms: Wait for payload initialization
            vTaskDelay(pdMS_TO_TICKS(INIT_WAIT_MS));

            // T+200ms: Check FAULT pin (should remain high-impedance = no fault)
            // For now, assume OK if DETECT still asserted
            if (read_detect_pin()) {
                state = PAYLOAD_STATE_READY;
                notify_event();
                ESP_LOGI(TAG, "Payload READY: %s", descriptor.name);
            } else {
                payload_power_off();
                state = PAYLOAD_STATE_FAULT;
                notify_event();
            }
            break;

        case PAYLOAD_STATE_READY:
            // Monitor for removal
            if (!read_detect_pin()) {
                ESP_LOGI(TAG, "Payload removal detected");
                state = PAYLOAD_STATE_REMOVING;
            }
            break;

        case PAYLOAD_STATE_REMOVING:
            payload_power_off();
            memset(&descriptor, 0, sizeof(descriptor));
            state = PAYLOAD_STATE_ABSENT;
            notify_event();
            ESP_LOGI(TAG, "Payload removed, power disabled");
            break;

        case PAYLOAD_STATE_FAULT:
            // Wait for physical removal to reset
            if (!read_detect_pin()) {
                vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));
                if (!read_detect_pin()) {
                    state = PAYLOAD_STATE_ABSENT;
                    ESP_LOGI(TAG, "Fault cleared (payload removed)");
                }
            }
            break;
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
