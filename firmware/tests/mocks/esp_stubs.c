// SPDX-License-Identifier: Apache-2.0
// Mock implementations for ESP-IDF functions used by firmware under test
#include "esp_stubs.h"
#include <string.h>

// --- LEDC mocks ---
static uint32_t ledc_duties[16] = {0};

esp_err_t ledc_timer_config(const ledc_timer_config_t *cfg) { (void)cfg; return ESP_OK; }
esp_err_t ledc_channel_config(const ledc_channel_config_t *cfg) { (void)cfg; return ESP_OK; }

esp_err_t ledc_set_duty(int mode, int channel, uint32_t duty) {
    (void)mode;
    if (channel < 16) ledc_duties[channel] = duty;
    return ESP_OK;
}

esp_err_t ledc_update_duty(int mode, int channel) {
    (void)mode; (void)channel;
    return ESP_OK;
}

// --- GPIO mocks ---
static int mock_gpio_levels[50] = {0};
static int mock_gpio_outputs[50] = {0};

esp_err_t gpio_config(const gpio_config_t *cfg) { (void)cfg; return ESP_OK; }

int gpio_get_level(int gpio) {
    if (gpio >= 0 && gpio < 50) return mock_gpio_levels[gpio];
    return 0;
}

esp_err_t gpio_set_level(int gpio, int level) {
    if (gpio >= 0 && gpio < 50) mock_gpio_outputs[gpio] = level;
    return ESP_OK;
}

esp_err_t gpio_install_isr_service(int flags) { (void)flags; return ESP_OK; }
esp_err_t gpio_isr_handler_add(int gpio, void (*handler)(void*), void *arg) {
    (void)gpio; (void)handler; (void)arg;
    return ESP_OK;
}

void mock_set_gpio_level(int gpio, int level) {
    if (gpio >= 0 && gpio < 50) mock_gpio_levels[gpio] = level;
}

int mock_get_gpio_output(int gpio) {
    if (gpio >= 0 && gpio < 50) return mock_gpio_outputs[gpio];
    return 0;
}

// --- Timer mocks ---
static int64_t mock_timer_value = 0;

int64_t esp_timer_get_time(void) { return mock_timer_value; }
void mock_set_timer(int64_t value) { mock_timer_value = value; }

// --- NVS mocks ---
#define NVS_MOCK_MAX_U8_ENTRIES 8
static struct { char key[32]; uint8_t value; bool set; } mock_nvs_u8[NVS_MOCK_MAX_U8_ENTRIES] = {0};

void mock_nvs_reset(void) {
    memset(mock_nvs_u8, 0, sizeof(mock_nvs_u8));
}

esp_err_t nvs_open(const char *ns, int mode, nvs_handle_t *handle) {
    (void)ns; (void)mode;
    *handle = 1;
    return ESP_OK;
}
void nvs_close(nvs_handle_t handle) { (void)handle; }
esp_err_t nvs_get_u32(nvs_handle_t handle, const char *key, uint32_t *out) {
    (void)handle; (void)key; (void)out;
    return ESP_FAIL;
}
esp_err_t nvs_set_u32(nvs_handle_t handle, const char *key, uint32_t value) {
    (void)handle; (void)key; (void)value;
    return ESP_OK;
}
esp_err_t nvs_commit(nvs_handle_t handle) { (void)handle; return ESP_OK; }
esp_err_t nvs_get_u8(nvs_handle_t handle, const char *key, uint8_t *out) {
    (void)handle;
    for (int i = 0; i < NVS_MOCK_MAX_U8_ENTRIES; i++) {
        if (mock_nvs_u8[i].set && strcmp(mock_nvs_u8[i].key, key) == 0) {
            *out = mock_nvs_u8[i].value;
            return ESP_OK;
        }
    }
    return ESP_FAIL;
}
esp_err_t nvs_set_u8(nvs_handle_t handle, const char *key, uint8_t value) {
    (void)handle;
    for (int i = 0; i < NVS_MOCK_MAX_U8_ENTRIES; i++) {
        if (mock_nvs_u8[i].set && strcmp(mock_nvs_u8[i].key, key) == 0) {
            mock_nvs_u8[i].value = value;
            return ESP_OK;
        }
    }
    for (int i = 0; i < NVS_MOCK_MAX_U8_ENTRIES; i++) {
        if (!mock_nvs_u8[i].set) {
            strncpy(mock_nvs_u8[i].key, key, sizeof(mock_nvs_u8[i].key) - 1);
            mock_nvs_u8[i].value = value;
            mock_nvs_u8[i].set = true;
            return ESP_OK;
        }
    }
    return ESP_FAIL;
}
esp_err_t nvs_erase_key(nvs_handle_t handle, const char *key) {
    (void)handle; (void)key;
    return ESP_OK;
}
esp_err_t nvs_get_str(nvs_handle_t handle, const char *key, char *out, size_t *length) {
    (void)handle; (void)key; (void)out; (void)length;
    return ESP_ERR_NOT_FOUND;
}
esp_err_t nvs_get_blob(nvs_handle_t handle, const char *key, void *out, size_t *length) {
    (void)handle; (void)key; (void)out; (void)length;
    return ESP_ERR_NOT_FOUND;
}
esp_err_t nvs_set_blob(nvs_handle_t handle, const char *key, const void *data, size_t length) {
    (void)handle; (void)key; (void)data; (void)length;
    return ESP_OK;
}

// --- PCNT mocks ---
static int mock_pcnt_counts[4] = {0};
static int pcnt_unit_idx = 0;

esp_err_t pcnt_new_unit(const pcnt_unit_config_t *cfg, pcnt_unit_handle_t *unit) {
    (void)cfg;
    *unit = (void*)(intptr_t)(pcnt_unit_idx % 4);
    pcnt_unit_idx++;
    return ESP_OK;
}
esp_err_t pcnt_new_channel(pcnt_unit_handle_t unit, const pcnt_chan_config_t *cfg, pcnt_channel_handle_t *ch) {
    (void)unit; (void)cfg;
    *ch = NULL;
    return ESP_OK;
}
esp_err_t pcnt_channel_set_edge_action(pcnt_channel_handle_t ch, int pos, int neg) {
    (void)ch; (void)pos; (void)neg; return ESP_OK;
}
esp_err_t pcnt_channel_set_level_action(pcnt_channel_handle_t ch, int high, int low) {
    (void)ch; (void)high; (void)low; return ESP_OK;
}
esp_err_t pcnt_unit_set_glitch_filter(pcnt_unit_handle_t unit, const pcnt_glitch_filter_config_t *cfg) {
    (void)unit; (void)cfg; return ESP_OK;
}
esp_err_t pcnt_unit_enable(pcnt_unit_handle_t unit) { (void)unit; return ESP_OK; }
esp_err_t pcnt_unit_clear_count(pcnt_unit_handle_t unit) { (void)unit; return ESP_OK; }
esp_err_t pcnt_unit_start(pcnt_unit_handle_t unit) { (void)unit; return ESP_OK; }

esp_err_t pcnt_unit_get_count(pcnt_unit_handle_t unit, int *count) {
    int idx = (int)(intptr_t)unit;
    if (idx >= 0 && idx < 4) {
        *count = mock_pcnt_counts[idx];
    } else {
        *count = 0;
    }
    return ESP_OK;
}

void mock_set_pcnt_count(int motor_id, int count) {
    if (motor_id >= 0 && motor_id < 4) mock_pcnt_counts[motor_id] = count;
}

void mock_reset_pcnt(void) {
    pcnt_unit_idx = 0;
    for (int i = 0; i < 4; i++) mock_pcnt_counts[i] = 0;
}

// --- ADC mocks ---
static int mock_adc_raw = 2048;
static int mock_adc_mv = 1500;
static int mock_adc_unit1_init_count = 0;

esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *cfg, adc_oneshot_unit_handle_t *handle) {
    (void)cfg;
    mock_adc_unit1_init_count++;
    if (mock_adc_unit1_init_count > 1) return ESP_ERR_INVALID_STATE;
    *handle = (void*)(intptr_t)1;
    return ESP_OK;
}

esp_err_t adc_manager_init(void) {
    if (mock_adc_unit1_init_count > 0) return ESP_OK;
    mock_adc_unit1_init_count = 1;
    return ESP_OK;
}

adc_oneshot_unit_handle_t adc_manager_get_handle(void) {
    return (void*)(intptr_t)1;
}
esp_err_t adc_manager_read(int channel, int *out_raw) {
    (void)channel;
    *out_raw = mock_adc_raw;
    return ESP_OK;
}
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t handle, int channel, const adc_oneshot_chan_cfg_t *cfg) {
    (void)handle; (void)channel; (void)cfg; return ESP_OK;
}
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t handle, int channel, int *raw) {
    (void)handle; (void)channel;
    *raw = mock_adc_raw;
    return ESP_OK;
}
esp_err_t adc_cali_create_scheme_line_fitting(const adc_cali_line_fitting_config_t *cfg, adc_cali_handle_t *handle) {
    (void)cfg; *handle = NULL; return ESP_OK;
}
esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *cfg, adc_cali_handle_t *handle) {
    (void)cfg; *handle = (void*)(intptr_t)2; return ESP_OK;
}
esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t handle, int raw, int *mv) {
    (void)handle; (void)raw;
    *mv = mock_adc_mv;
    return ESP_OK;
}

void mock_set_adc_raw(int raw_value) { mock_adc_raw = raw_value; }
void mock_set_adc_voltage_mv(int mv) { mock_adc_mv = mv; }

// --- FreeRTOS stubs ---
void vTaskDelay(int ticks) { (void)ticks; }

// --- WiFi mocks ---
#include "esp_wifi.h"
static int8_t mock_wifi_rssi_val = -50;
static int mock_wifi_connected_val = 1;

int esp_wifi_sta_get_ap_info(wifi_ap_record_t *ap_info) {
    if (!mock_wifi_connected_val) return -1;
    ap_info->rssi = mock_wifi_rssi_val;
    return 0;
}
void mock_set_wifi_rssi(int8_t rssi) { mock_wifi_rssi_val = rssi; }
void mock_set_wifi_connected(int connected) { mock_wifi_connected_val = connected; }
int esp_wifi_stop(void) { return 0; }

// --- System info stubs ---
uint32_t esp_get_free_heap_size(void) { return 128000; }
uint32_t esp_get_minimum_free_heap_size(void) { return 96000; }
