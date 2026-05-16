// SPDX-License-Identifier: Apache-2.0
#include "display.h"
#include "i2c_bus.h"
#include "pin_definitions.h"
#include "battery.h"
#include "safety.h"
#include "encoder.h"
#include "imu.h"
#include "thermal_monitor.h"
#include "dtls_transport.h"

#ifndef UNIT_TEST_BUILD
#include "ota_update.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_app_desc.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "ssd1306.h"
#endif

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/i2c.h"

#include <string.h>
#include <stdio.h>
#include <math.h>

#ifdef UNIT_TEST_BUILD
// Stubs for headers guarded out in test builds
typedef struct { uint8_t status; uint8_t progress_pct; uint32_t bytes_received; uint32_t bytes_total; char error_msg[64]; } ota_progress_t;
#define OTA_STATUS_IDLE 0
extern ota_progress_t ota_update_get_progress(void);
#endif

static const char *TAG = "display";

// MCP23017 register addresses
#define MCP_IODIRA   0x00
#define MCP_IODIRB   0x01
#define MCP_GPPUA    0x0C
#define MCP_GPPUB    0x0D
#define MCP_GPIOA    0x12
#define MCP_GPIOB    0x13

// SH1106 display dimensions
#define DISPLAY_WIDTH   128
#define DISPLAY_HEIGHT  64

// Button state
typedef struct {
    bool     raw;
    bool     pressed;
    bool     prev_pressed;
    uint32_t last_change_ms;
    uint32_t press_start_ms;
} button_state_t;

// Module state
static display_page_t s_current_page = DISPLAY_PAGE_HOME;
static button_state_t s_btn_up   = {0};
static button_state_t s_btn_down = {0};
static button_state_t s_btn_ok   = {0};

static display_fault_entry_t s_fault_log[DISPLAY_FAULT_LOG_SIZE];
static uint8_t s_fault_log_head = 0;
static uint8_t s_fault_log_count = 0;
static portMUX_TYPE s_fault_spinlock = portMUX_INITIALIZER_UNLOCKED;

#ifndef UNIT_TEST_BUILD
static SSD1306_t s_dev;
static bool s_hw_initialized = false;
#endif

// Forward declarations
static void buttons_read(uint32_t now_ms);
static void debounce_button(button_state_t *btn, uint32_t now_ms);
static bool button_just_pressed(button_state_t *btn);
static bool button_is_long_pressed(const button_state_t *btn, uint32_t now_ms);
static void handle_navigation(uint32_t now_ms);
static void render_current_page(void);
static void render_page_home(void);
static void render_page_motion(void);
static void render_page_faults(void);
static void render_page_system(void);
static void render_page_network(void);
static void trigger_wifi_reset(void);

// Display hardware abstraction
static void display_hw_clear(void);
static void display_hw_show(void);
static void display_hw_draw_string(int line, const char *str);

// -------------------------------------------------------------------
// Initialization
// -------------------------------------------------------------------

esp_err_t display_init(void)
{
    if (!i2c_bus_lock()) {
        return ESP_ERR_TIMEOUT;
    }

    // Probe SH1106 by attempting a write
    uint8_t probe = 0x00;
    esp_err_t ret = i2c_master_write_to_device(
        I2C_NUM_0, DISPLAY_I2C_ADDR, &probe, 1, pdMS_TO_TICKS(50));
    i2c_bus_unlock();

    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "OLED not found at 0x%02X", DISPLAY_I2C_ADDR);
        return ret;
    }

    // Configure MCP23017 button pins.
    // mcp23017_read_register manages its own I2C locking — do NOT hold
    // the bus lock around these calls (non-recursive mutex would deadlock).

    // GPA4 (OK button) — ensure direction is input
    uint8_t iodira = 0;
    mcp23017_read_register(MCP23017_ADDR, MCP_IODIRA, &iodira);
    iodira |= (1 << DISPLAY_BTN_OK_BIT);
    if (i2c_bus_lock()) {
        uint8_t buf_dir_a[2] = { MCP_IODIRA, iodira };
        i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, buf_dir_a, 2, pdMS_TO_TICKS(50));
        i2c_bus_unlock();
    }

    // GPA4 pull-up enabled
    uint8_t gppua = 0;
    mcp23017_read_register(MCP23017_ADDR, MCP_GPPUA, &gppua);
    gppua |= (1 << DISPLAY_BTN_OK_BIT);
    if (i2c_bus_lock()) {
        uint8_t buf_a[2] = { MCP_GPPUA, gppua };
        i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, buf_a, 2, pdMS_TO_TICKS(50));
        i2c_bus_unlock();
    }

    // GPB6 (UP), GPB7 (DOWN) — ensure direction is input
    uint8_t iodirb = 0;
    mcp23017_read_register(MCP23017_ADDR, MCP_IODIRB, &iodirb);
    iodirb |= (1 << DISPLAY_BTN_UP_BIT) | (1 << DISPLAY_BTN_DOWN_BIT);
    if (i2c_bus_lock()) {
        uint8_t buf_dir[2] = { MCP_IODIRB, iodirb };
        i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, buf_dir, 2, pdMS_TO_TICKS(50));
        i2c_bus_unlock();
    }

    // GPB6, GPB7 pull-ups enabled
    uint8_t gppub = 0;
    mcp23017_read_register(MCP23017_ADDR, MCP_GPPUB, &gppub);
    gppub |= (1 << DISPLAY_BTN_UP_BIT) | (1 << DISPLAY_BTN_DOWN_BIT);
    if (i2c_bus_lock()) {
        uint8_t buf_b[2] = { MCP_GPPUB, gppub };
        i2c_master_write_to_device(I2C_NUM_0, MCP23017_ADDR, buf_b, 2, pdMS_TO_TICKS(50));
        i2c_bus_unlock();
    }

#ifndef UNIT_TEST_BUILD
    // Initialize SSD1306/SH1106 driver
    if (i2c_bus_lock()) {
        ssd1306_init(&s_dev, DISPLAY_WIDTH, DISPLAY_HEIGHT);
        ssd1306_contrast(&s_dev, 0xFF);
        ssd1306_clear_screen(&s_dev, false);
        i2c_bus_unlock();
        s_hw_initialized = true;
    }
#endif

    ESP_LOGI(TAG, "Display initialized (SH1106 128x64 @ 0x%02X)", DISPLAY_I2C_ADDR);
    return ESP_OK;
}

// -------------------------------------------------------------------
// Task
// -------------------------------------------------------------------

void display_task(void *params)
{
    (void)params;
    TickType_t last_wake = xTaskGetTickCount();

#ifdef CONFIG_DISPLAY_REFRESH_MS
    const TickType_t period = pdMS_TO_TICKS(CONFIG_DISPLAY_REFRESH_MS);
#else
    const TickType_t period = pdMS_TO_TICKS(200);
#endif

    while (1) {
        uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);

        buttons_read(now_ms);
        handle_navigation(now_ms);
        render_current_page();

        vTaskDelayUntil(&last_wake, period);
    }
}

// -------------------------------------------------------------------
// Buttons
// -------------------------------------------------------------------

static void buttons_read(uint32_t now_ms)
{
    uint8_t gpioa = 0xFF;
    uint8_t gpiob = 0xFF;

    mcp23017_read_register(MCP23017_ADDR, MCP_GPIOA, &gpioa);
    mcp23017_read_register(MCP23017_ADDR, MCP_GPIOB, &gpiob);

    // Active-low: pressed when bit is 0
    s_btn_ok.raw   = !(gpioa & (1 << DISPLAY_BTN_OK_BIT));
    s_btn_up.raw   = !(gpiob & (1 << DISPLAY_BTN_UP_BIT));
    s_btn_down.raw = !(gpiob & (1 << DISPLAY_BTN_DOWN_BIT));

    debounce_button(&s_btn_up, now_ms);
    debounce_button(&s_btn_down, now_ms);
    debounce_button(&s_btn_ok, now_ms);
}

static void debounce_button(button_state_t *btn, uint32_t now_ms)
{
    if (btn->raw != btn->pressed) {
        if ((now_ms - btn->last_change_ms) >= DISPLAY_BTN_DEBOUNCE_MS) {
            btn->prev_pressed = btn->pressed;
            btn->pressed = btn->raw;
            btn->last_change_ms = now_ms;
            if (btn->pressed) {
                btn->press_start_ms = now_ms;
            }
        }
    } else {
        btn->last_change_ms = now_ms;
    }
}

static bool button_just_pressed(button_state_t *btn)
{
    if (btn->pressed && !btn->prev_pressed) {
        btn->prev_pressed = btn->pressed;
        return true;
    }
    return false;
}

static bool button_is_long_pressed(const button_state_t *btn, uint32_t now_ms)
{
    return btn->pressed && ((now_ms - btn->press_start_ms) >= DISPLAY_LONG_PRESS_MS);
}

// -------------------------------------------------------------------
// Navigation
// -------------------------------------------------------------------

static void handle_navigation(uint32_t now_ms)
{
    if (button_is_long_pressed(&s_btn_ok, now_ms)) {
        trigger_wifi_reset();
        return;
    }

    if (button_just_pressed(&s_btn_down)) {
        s_current_page = (display_page_t)((s_current_page + 1) % DISPLAY_PAGE_COUNT);
    }

    if (button_just_pressed(&s_btn_up)) {
        s_current_page = (display_page_t)((s_current_page + DISPLAY_PAGE_COUNT - 1) % DISPLAY_PAGE_COUNT);
    }
}

display_page_t display_get_current_page(void)
{
    return s_current_page;
}

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------

static void render_current_page(void)
{
    display_hw_clear();

    switch (s_current_page) {
        case DISPLAY_PAGE_HOME:    render_page_home();    break;
        case DISPLAY_PAGE_MOTION:  render_page_motion();  break;
        case DISPLAY_PAGE_FAULTS:  render_page_faults();  break;
        case DISPLAY_PAGE_SYSTEM:  render_page_system();  break;
        case DISPLAY_PAGE_NETWORK: render_page_network(); break;
        default: break;
    }

    // Page indicator on line 7 (bottom)
    char indicator[22];
    memset(indicator, ' ', sizeof(indicator));
    for (int i = 0; i < DISPLAY_PAGE_COUNT; i++) {
        indicator[i * 2] = (i == (int)s_current_page) ? '[' : ' ';
        indicator[i * 2 + 1] = (i == (int)s_current_page) ? ']' : '.';
    }
    indicator[DISPLAY_PAGE_COUNT * 2] = '\0';
    display_hw_draw_string(7, indicator);

    display_hw_show();
}

static void render_page_home(void)
{
    char buf[22];

    display_hw_draw_string(0, "== HOME ==");

    battery_system_state_t bs = battery_get_system_state();
    snprintf(buf, sizeof(buf), "BAT: %d%% %.2fV",
             bs.total_percentage,
             bs.packs[0].present ? (double)bs.packs[0].voltage : 0.0);
    display_hw_draw_string(1, buf);

    safety_state_t ss = safety_get_state();
    const char *safety_str = "NORMAL";
    switch (ss) {
        case SAFETY_ESTOPPED:        safety_str = "E-STOP"; break;
        case SAFETY_RECOVERY_PENDING: safety_str = "RECOV";  break;
        case SAFETY_RELAY_FAULT:     safety_str = "FAULT";  break;
        default: break;
    }
    snprintf(buf, sizeof(buf), "SAFE: %s", safety_str);
    display_hw_draw_string(2, buf);

#ifndef UNIT_TEST_BUILD
    wifi_ap_record_t ap = {0};
    esp_wifi_sta_get_ap_info(&ap);
    snprintf(buf, sizeof(buf), "%.16s", (char *)ap.ssid);
    display_hw_draw_string(4, buf);

    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_ip_info_t ip = {0};
    if (netif) {
        esp_netif_get_ip_info(netif, &ip);
    }
    snprintf(buf, sizeof(buf), IPSTR, IP2STR(&ip.ip));
    display_hw_draw_string(5, buf);
#else
    display_hw_draw_string(4, "WiFi: N/A");
    display_hw_draw_string(5, "0.0.0.0");
#endif
}

static void render_page_motion(void)
{
    char buf[22];

    display_hw_draw_string(0, "== MOTION ==");

    float rpm_fl = encoder_get_speed_rps(MOTOR_FL) * 60.0f;
    float rpm_fr = encoder_get_speed_rps(MOTOR_FR) * 60.0f;
    float rpm_rl = encoder_get_speed_rps(MOTOR_RL) * 60.0f;
    float rpm_rr = encoder_get_speed_rps(MOTOR_RR) * 60.0f;

    snprintf(buf, sizeof(buf), "FL:%+4.0f FR:%+4.0f", (double)rpm_fl, (double)rpm_fr);
    display_hw_draw_string(2, buf);
    snprintf(buf, sizeof(buf), "RL:%+4.0f RR:%+4.0f", (double)rpm_rl, (double)rpm_rr);
    display_hw_draw_string(3, buf);

    euler_t euler = {0};
    imu_read_euler(&euler);
    float heading_deg = euler.yaw * (180.0f / 3.14159265f);
    snprintf(buf, sizeof(buf), "HDG: %.1f deg", (double)heading_deg);
    display_hw_draw_string(5, buf);
}

static void render_page_faults(void)
{
    char buf[22];

    display_hw_draw_string(0, "== FAULTS ==");

    portENTER_CRITICAL(&s_fault_spinlock);
    uint8_t count = s_fault_log_count;
    display_fault_entry_t entries[DISPLAY_FAULT_LOG_SIZE];
    for (int i = 0; i < DISPLAY_FAULT_LOG_SIZE; i++) {
        entries[i] = s_fault_log[i];
    }
    uint8_t head = s_fault_log_head;
    portEXIT_CRITICAL(&s_fault_spinlock);

    if (count == 0) {
        display_hw_draw_string(3, "  No faults");
        return;
    }

    for (int i = 0; i < DISPLAY_FAULT_LOG_SIZE && i < count; i++) {
        uint8_t idx = (head + DISPLAY_FAULT_LOG_SIZE - 1 - i) % DISPLAY_FAULT_LOG_SIZE;
        uint32_t t = entries[idx].timestamp_ms / 1000;
        uint32_t m = (t / 60) % 60;
        uint32_t s = t % 60;
        snprintf(buf, sizeof(buf), "%02lu:%02lu %.14s",
                 (unsigned long)m, (unsigned long)s, entries[idx].msg);
        display_hw_draw_string(2 + i, buf);
    }
}

static void render_page_system(void)
{
    char buf[22];

    display_hw_draw_string(0, "== SYSTEM ==");

#ifndef UNIT_TEST_BUILD
    const esp_app_desc_t *app = esp_app_get_description();
    snprintf(buf, sizeof(buf), "FW: %s", app->version);
#else
    snprintf(buf, sizeof(buf), "FW: 0.0.0-test");
#endif
    display_hw_draw_string(1, buf);

    int64_t uptime_us = esp_timer_get_time();
    uint32_t up_s = (uint32_t)(uptime_us / 1000000);
    uint32_t h = up_s / 3600;
    uint32_t m = (up_s / 60) % 60;
    uint32_t s = up_s % 60;
    snprintf(buf, sizeof(buf), "UP: %luh %02lum %02lus",
             (unsigned long)h, (unsigned long)m, (unsigned long)s);
    display_hw_draw_string(3, buf);

    uint32_t heap_free = esp_get_free_heap_size() / 1024;
    uint32_t heap_min = esp_get_minimum_free_heap_size() / 1024;
    snprintf(buf, sizeof(buf), "HEAP: %luk min:%luk",
             (unsigned long)heap_free, (unsigned long)heap_min);
    display_hw_draw_string(5, buf);

    thermal_reading_t tr = {0};
    thermal_get_reading(&tr);
    snprintf(buf, sizeof(buf), "TEMP: %.1fC", (double)tr.effective_temp_c);
    display_hw_draw_string(6, buf);
}

static void render_page_network(void)
{
    char buf[22];

    display_hw_draw_string(0, "== NETWORK ==");

#ifndef MICROROS_DISABLED
    display_hw_draw_string(1, "uROS: enabled");
#else
    display_hw_draw_string(1, "uROS: disabled");
#endif

    uint8_t sessions = dtls_active_session_count();
    snprintf(buf, sizeof(buf), "DTLS: %d sessions", sessions);
    display_hw_draw_string(3, buf);

    ota_progress_t ota = ota_update_get_progress();
    if (ota.status != OTA_STATUS_IDLE) {
        snprintf(buf, sizeof(buf), "OTA: %d%%", ota.progress_pct);
    } else {
        snprintf(buf, sizeof(buf), "OTA: idle");
    }
    display_hw_draw_string(5, buf);

#ifndef UNIT_TEST_BUILD
    wifi_ap_record_t ap = {0};
    esp_wifi_sta_get_ap_info(&ap);
    snprintf(buf, sizeof(buf), "RSSI: %ddBm", ap.rssi);
    display_hw_draw_string(6, buf);
#else
    display_hw_draw_string(6, "RSSI: N/A");
#endif
}

// -------------------------------------------------------------------
// Fault log
// -------------------------------------------------------------------

void display_log_fault(display_fault_source_t source, uint8_t code, const char *msg)
{
    portENTER_CRITICAL(&s_fault_spinlock);

    display_fault_entry_t *entry = &s_fault_log[s_fault_log_head];
    entry->timestamp_ms = (uint32_t)(esp_timer_get_time() / 1000);
    entry->source = (uint8_t)source;
    entry->code = code;
    strncpy(entry->msg, msg ? msg : "", sizeof(entry->msg) - 1);
    entry->msg[sizeof(entry->msg) - 1] = '\0';

    s_fault_log_head = (s_fault_log_head + 1) % DISPLAY_FAULT_LOG_SIZE;
    if (s_fault_log_count < DISPLAY_FAULT_LOG_SIZE) {
        s_fault_log_count++;
    }

    portEXIT_CRITICAL(&s_fault_spinlock);
}

// -------------------------------------------------------------------
// WiFi reset (OK long-press 3s)
// -------------------------------------------------------------------

static void trigger_wifi_reset(void)
{
    ESP_LOGW(TAG, "WiFi reset triggered via display button long-press");

#ifndef UNIT_TEST_BUILD
    nvs_handle_t nvs;
    if (nvs_open("wifi", NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_erase_all(nvs);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
#endif

    vTaskDelay(pdMS_TO_TICKS(100));
    esp_restart();
}

// -------------------------------------------------------------------
// Display hardware abstraction
// -------------------------------------------------------------------

static void display_hw_clear(void)
{
#ifndef UNIT_TEST_BUILD
    if (!s_hw_initialized) return;
    if (!i2c_bus_lock()) return;
    ssd1306_clear_screen(&s_dev, false);
    i2c_bus_unlock();
#endif
}

static void display_hw_show(void)
{
#ifndef UNIT_TEST_BUILD
    if (!s_hw_initialized) return;
    if (!i2c_bus_lock()) return;
    ssd1306_show_buffer(&s_dev);
    i2c_bus_unlock();
#endif
}

static void display_hw_draw_string(int line, const char *str)
{
#ifndef UNIT_TEST_BUILD
    if (!s_hw_initialized) return;
    if (!i2c_bus_lock()) return;
    ssd1306_display_text(&s_dev, line, str, strlen(str), false);
    i2c_bus_unlock();
#else
    (void)line;
    (void)str;
#endif
}

