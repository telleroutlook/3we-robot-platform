// SPDX-License-Identifier: Apache-2.0
// Minimal ESP-IDF type stubs for host-side unit testing
#ifndef ESP_STUBS_H
#define ESP_STUBS_H

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>

// esp_err_t
typedef int esp_err_t;
#define ESP_OK              0
#define ESP_FAIL            (-1)
#define ESP_ERR_NO_MEM      0x0101
#define ESP_ERR_INVALID_ARG 0x0102
#define ESP_ERR_INVALID_STATE 0x0103
#define ESP_ERR_NOT_FOUND   0x0105
#define ESP_ERR_TIMEOUT     0x0107
#define ESP_ERR_INVALID_RESPONSE 0x0108
#define ESP_ERROR_CHECK(x)  do { (void)(x); } while(0)

static inline const char *esp_err_to_name(esp_err_t err) { (void)err; return "MOCK_ERR"; }

#define GPIO_MODE_OUTPUT    1

// Logging stubs
#define ESP_LOGI(tag, fmt, ...)  ((void)0)
#define ESP_LOGW(tag, fmt, ...)  ((void)0)
#define ESP_LOGE(tag, fmt, ...)  ((void)0)
#define ESP_LOGD(tag, fmt, ...)  ((void)0)

// IRAM_ATTR
#define IRAM_ATTR

// Allow test stubs to override firmware functions
#define TESTABLE_WEAK __attribute__((weak))

// LEDC stubs
typedef int ledc_channel_t;
typedef int ledc_mode_t;
#define LEDC_LOW_SPEED_MODE 0
#define LEDC_TIMER_0        0
#define LEDC_AUTO_CLK       0

typedef struct {
    int speed_mode;
    int duty_resolution;
    int timer_num;
    int freq_hz;
    int clk_cfg;
} ledc_timer_config_t;

typedef struct {
    int speed_mode;
    int channel;
    int timer_sel;
    int gpio_num;
    int duty;
    int hpoint;
} ledc_channel_config_t;

esp_err_t ledc_timer_config(const ledc_timer_config_t *cfg);
esp_err_t ledc_channel_config(const ledc_channel_config_t *cfg);
esp_err_t ledc_set_duty(int mode, int channel, uint32_t duty);
esp_err_t ledc_update_duty(int mode, int channel);

// GPIO stubs
typedef int gpio_num_t;
#define GPIO_MODE_INPUT       0
#define GPIO_PULLUP_ENABLE    1
#define GPIO_PULLUP_DISABLE   0
#define GPIO_PULLDOWN_ENABLE  1
#define GPIO_PULLDOWN_DISABLE 0
#define GPIO_INTR_NEGEDGE     2
#define GPIO_INTR_DISABLE     0

typedef struct {
    uint64_t pin_bit_mask;
    int mode;
    int pull_up_en;
    int pull_down_en;
    int intr_type;
} gpio_config_t;

esp_err_t gpio_config(const gpio_config_t *cfg);
int gpio_get_level(int gpio);
esp_err_t gpio_set_level(int gpio, int level);
esp_err_t gpio_install_isr_service(int flags);
esp_err_t gpio_isr_handler_add(int gpio, void (*handler)(void*), void *arg);
void mock_set_gpio_level(int gpio, int level);
int mock_get_gpio_output(int gpio);

// Timer stubs
int64_t esp_timer_get_time(void);
void mock_set_timer(int64_t value);

// NVS stubs
typedef int nvs_handle_t;
#define NVS_READONLY        0
#define NVS_READWRITE       1
#define ESP_ERR_NVS_NOT_FOUND 0x1102
esp_err_t nvs_open(const char *ns, int mode, nvs_handle_t *handle);
void nvs_close(nvs_handle_t handle);
esp_err_t nvs_get_u32(nvs_handle_t handle, const char *key, uint32_t *out);
esp_err_t nvs_set_u32(nvs_handle_t handle, const char *key, uint32_t value);
esp_err_t nvs_get_u8(nvs_handle_t handle, const char *key, uint8_t *out);
esp_err_t nvs_set_u8(nvs_handle_t handle, const char *key, uint8_t value);
esp_err_t nvs_get_str(nvs_handle_t handle, const char *key, char *out, size_t *length);
esp_err_t nvs_get_blob(nvs_handle_t handle, const char *key, void *out, size_t *length);
esp_err_t nvs_set_blob(nvs_handle_t handle, const char *key, const void *data, size_t length);
esp_err_t nvs_erase_key(nvs_handle_t handle, const char *key);
esp_err_t nvs_commit(nvs_handle_t handle);

// PCNT stubs
typedef void* pcnt_unit_handle_t;
typedef void* pcnt_channel_handle_t;

typedef struct { int high_limit; int low_limit; } pcnt_unit_config_t;
typedef struct { int edge_gpio_num; int level_gpio_num; } pcnt_chan_config_t;
typedef struct { int max_glitch_ns; } pcnt_glitch_filter_config_t;

#define PCNT_CHANNEL_EDGE_ACTION_DECREASE 0
#define PCNT_CHANNEL_EDGE_ACTION_INCREASE 1
#define PCNT_CHANNEL_LEVEL_ACTION_KEEP    0
#define PCNT_CHANNEL_LEVEL_ACTION_INVERSE 1

esp_err_t pcnt_new_unit(const pcnt_unit_config_t *cfg, pcnt_unit_handle_t *unit);
esp_err_t pcnt_new_channel(pcnt_unit_handle_t unit, const pcnt_chan_config_t *cfg, pcnt_channel_handle_t *ch);
esp_err_t pcnt_channel_set_edge_action(pcnt_channel_handle_t ch, int pos, int neg);
esp_err_t pcnt_channel_set_level_action(pcnt_channel_handle_t ch, int high, int low);
esp_err_t pcnt_unit_set_glitch_filter(pcnt_unit_handle_t unit, const pcnt_glitch_filter_config_t *cfg);
esp_err_t pcnt_unit_enable(pcnt_unit_handle_t unit);
esp_err_t pcnt_unit_clear_count(pcnt_unit_handle_t unit);
esp_err_t pcnt_unit_start(pcnt_unit_handle_t unit);
esp_err_t pcnt_unit_get_count(pcnt_unit_handle_t unit, int *count);

void mock_set_pcnt_count(int motor_id, int count);
void mock_reset_pcnt(void);

// ADC stubs
typedef void* adc_oneshot_unit_handle_t;
typedef void* adc_cali_handle_t;
#define ADC_UNIT_1        0
#define ADC_ATTEN_DB_11   3
#define ADC_ATTEN_DB_12   3
#define ADC_BITWIDTH_12   12
#define ADC_CHANNEL_0     0
#define ADC_CHANNEL_1     1
#define ADC_CHANNEL_2     2
#define ADC_CHANNEL_3     3
#define ADC_CHANNEL_4     4
#define ADC_CHANNEL_5     5
#define ADC_CHANNEL_6     6
#define ADC_CHANNEL_7     7
#define ADC_CHANNEL_8     8
#define ADC_CHANNEL_9     9

typedef struct { int unit_id; } adc_oneshot_unit_init_cfg_t;
typedef struct { int atten; int bitwidth; } adc_oneshot_chan_cfg_t;
typedef struct { int unit_id; int atten; int bitwidth; } adc_cali_line_fitting_config_t;
typedef adc_cali_line_fitting_config_t adc_cali_curve_fitting_config_t;

esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *cfg, adc_oneshot_unit_handle_t *handle);
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t handle, int channel, const adc_oneshot_chan_cfg_t *cfg);
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t handle, int channel, int *raw);
esp_err_t adc_cali_create_scheme_line_fitting(const adc_cali_line_fitting_config_t *cfg, adc_cali_handle_t *handle);
esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *cfg, adc_cali_handle_t *handle);
esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t handle, int raw, int *mv);

// ADC manager stubs
esp_err_t adc_manager_init(void);
adc_oneshot_unit_handle_t adc_manager_get_handle(void);

void mock_set_adc_raw(int raw_value);
void mock_set_adc_voltage_mv(int mv);

// FreeRTOS stubs
#define pdMS_TO_TICKS(x) (x)
#define portTICK_PERIOD_MS 1
#define pdTRUE  1
#define pdFALSE 0
typedef int TickType_t;
static inline TickType_t xTaskGetTickCount(void) { return 0; }
void vTaskDelay(int ticks);
static inline void vTaskDelete(void *handle) { (void)handle; }

// FreeRTOS spinlock stubs
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(mux)      ((void)(mux))
#define portEXIT_CRITICAL(mux)       ((void)(mux))
#define portENTER_CRITICAL_ISR(mux)  ((void)(mux))
#define portEXIT_CRITICAL_ISR(mux)   ((void)(mux))

// UART stub
#define UART_NUM_1 1

// NVS mock reset (clears all stored u8 values)
void mock_nvs_reset(void);

#endif // ESP_STUBS_H
