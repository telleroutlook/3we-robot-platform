// SPDX-License-Identifier: Apache-2.0
#include "canbus.h"
#include "pin_definitions.h"

#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include <string.h>

static const char *TAG = "canbus";

// MCP2515 registers
#define MCP_CANSTAT     0x0E
#define MCP_CANCTRL     0x0F
#define MCP_CNF3        0x28
#define MCP_CNF2        0x29
#define MCP_CNF1        0x2A
#define MCP_CANINTE     0x2B
#define MCP_CANINTF     0x2C
#define MCP_TXB0CTRL    0x30
#define MCP_TXB0SIDH    0x31
#define MCP_TXB0DLC     0x35
#define MCP_TXB0D0      0x36
#define MCP_RXB0CTRL    0x60
#define MCP_RXB0SIDH    0x61
#define MCP_RXB0DLC     0x65
#define MCP_RXB0D0      0x66
#define MCP_RXM0SIDH    0x20
#define MCP_RXF0SIDH    0x00

// MCP2515 SPI instructions
#define MCP_RESET       0xC0
#define MCP_READ        0x03
#define MCP_WRITE       0x02
#define MCP_RTS_TXB0    0x81
#define MCP_READ_STATUS 0xA0
#define MCP_BIT_MODIFY  0x05
#define MCP_READ_RX0    0x90

// CANCTRL modes
#define MODE_NORMAL     0x00
#define MODE_SLEEP      0x20
#define MODE_LOOPBACK   0x40
#define MODE_LISTEN     0x60
#define MODE_CONFIG     0x80
#define MODE_MASK       0xE0

// CANINTF flags
#define CANINTF_RX0IF   0x01
#define CANINTF_TX0IF   0x04
#define CANINTF_ERRIF   0x20
#define CANINTF_MERRF   0x80

// CANINTE enable flags
#define CANINTE_RX0IE   0x01
#define CANINTE_TX0IE   0x04
#define CANINTE_ERRIE   0x20

// EFLG error flags
#define MCP_EFLG        0x2D
#define EFLG_TXBO       0x20
#define MCP_TEC         0x1C

static spi_device_handle_t spi_dev;
static canbus_config_t current_config;
static can_recv_callback_t recv_callback = NULL;
static SemaphoreHandle_t spi_mutex;
static bool ready = false;

static esp_err_t mcp2515_write_reg(uint8_t reg, uint8_t value)
{
    uint8_t tx[3] = { MCP_WRITE, reg, value };
    spi_transaction_t t = {
        .length = 24,
        .tx_buffer = tx,
    };
    xSemaphoreTake(spi_mutex, portMAX_DELAY);
    esp_err_t ret = spi_device_polling_transmit(spi_dev, &t);
    xSemaphoreGive(spi_mutex);
    return ret;
}

static esp_err_t mcp2515_write_reg_unlocked(uint8_t reg, uint8_t value)
{
    uint8_t tx[3] = { MCP_WRITE, reg, value };
    spi_transaction_t t = {
        .length = 24,
        .tx_buffer = tx,
    };
    return spi_device_polling_transmit(spi_dev, &t);
}

static uint8_t mcp2515_read_reg(uint8_t reg)
{
    uint8_t tx[3] = { MCP_READ, reg, 0x00 };
    uint8_t rx[3] = {0};
    spi_transaction_t t = {
        .length = 24,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    xSemaphoreTake(spi_mutex, portMAX_DELAY);
    spi_device_polling_transmit(spi_dev, &t);
    xSemaphoreGive(spi_mutex);
    return rx[2];
}

static void mcp2515_bit_modify(uint8_t reg, uint8_t mask, uint8_t value)
{
    uint8_t tx[4] = { MCP_BIT_MODIFY, reg, mask, value };
    spi_transaction_t t = {
        .length = 32,
        .tx_buffer = tx,
    };
    xSemaphoreTake(spi_mutex, portMAX_DELAY);
    spi_device_polling_transmit(spi_dev, &t);
    xSemaphoreGive(spi_mutex);
}

static void mcp2515_reset(void)
{
    uint8_t tx[1] = { MCP_RESET };
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = tx,
    };
    xSemaphoreTake(spi_mutex, portMAX_DELAY);
    spi_device_polling_transmit(spi_dev, &t);
    xSemaphoreGive(spi_mutex);
    vTaskDelay(pdMS_TO_TICKS(10));
}

static esp_err_t mcp2515_set_bitrate(uint32_t bitrate)
{
    // CNF values for 8MHz oscillator (typical MCP2515 crystal)
    uint8_t cnf1, cnf2, cnf3;

    switch (bitrate) {
    case CAN_BITRATE_125K:
        cnf1 = 0x03; cnf2 = 0xF0; cnf3 = 0x86;
        break;
    case CAN_BITRATE_250K:
        cnf1 = 0x01; cnf2 = 0xF0; cnf3 = 0x86;
        break;
    case CAN_BITRATE_500K:
        cnf1 = 0x00; cnf2 = 0xF0; cnf3 = 0x86;
        break;
    case CAN_BITRATE_1M:
        cnf1 = 0x00; cnf2 = 0xD0; cnf3 = 0x82;
        break;
    default:
        ESP_LOGE(TAG, "Unsupported bitrate: %lu", (unsigned long)bitrate);
        return ESP_ERR_INVALID_ARG;
    }

    mcp2515_write_reg(MCP_CNF1, cnf1);
    mcp2515_write_reg(MCP_CNF2, cnf2);
    mcp2515_write_reg(MCP_CNF3, cnf3);
    return ESP_OK;
}

static bool mcp2515_set_mode(uint8_t mode)
{
    mcp2515_bit_modify(MCP_CANCTRL, MODE_MASK, mode);
    vTaskDelay(pdMS_TO_TICKS(10));

    uint8_t actual = mcp2515_read_reg(MCP_CANSTAT) & MODE_MASK;
    return actual == mode;
}

esp_err_t canbus_init(const canbus_config_t *config)
{
    if (!config) return ESP_ERR_INVALID_ARG;
    memcpy(&current_config, config, sizeof(canbus_config_t));

    spi_mutex = xSemaphoreCreateMutex();
    if (!spi_mutex) {
        ESP_LOGE(TAG, "Failed to create SPI mutex");
        return ESP_ERR_NO_MEM;
    }

    // Configure SPI bus
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = config->pin_mosi,
        .miso_io_num = config->pin_miso,
        .sclk_io_num = config->pin_sclk,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 16,
    };

    esp_err_t ret = spi_bus_initialize(config->spi_host, &bus_cfg, SPI_DMA_DISABLED);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 10 * 1000 * 1000,  // 10 MHz
        .mode = 0,
        .spics_io_num = config->pin_cs,
        .queue_size = 4,
    };

    ret = spi_bus_add_device(config->spi_host, &dev_cfg, &spi_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI device add failed: %s", esp_err_to_name(ret));
        return ret;
    }

    // Configure INT pin as input
    gpio_config_t int_cfg = {
        .pin_bit_mask = (1ULL << config->pin_int),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&int_cfg);

    // Reset MCP2515
    mcp2515_reset();

    // Verify communication (should be in config mode after reset)
    uint8_t stat = mcp2515_read_reg(MCP_CANSTAT);
    if ((stat & MODE_MASK) != MODE_CONFIG) {
        ESP_LOGE(TAG, "MCP2515 not in config mode after reset (0x%02X)", stat);
        return ESP_FAIL;
    }

    // Set bitrate
    ret = mcp2515_set_bitrate(config->bitrate);
    if (ret != ESP_OK) return ret;

    // Configure acceptance mask and filter
    mcp2515_write_reg(MCP_RXM0SIDH, (config->accept_mask >> 3) & 0xFF);
    mcp2515_write_reg(MCP_RXM0SIDH + 1, ((config->accept_mask & 0x07) << 5));
    mcp2515_write_reg(MCP_RXF0SIDH, (config->accept_filter >> 3) & 0xFF);
    mcp2515_write_reg(MCP_RXF0SIDH + 1, ((config->accept_filter & 0x07) << 5));

    // RXB0: receive all valid messages matching filter
    mcp2515_write_reg(MCP_RXB0CTRL, 0x00);

    // Enable RX interrupt
    mcp2515_write_reg(MCP_CANINTE, CANINTE_RX0IE | CANINTE_ERRIE);

    // Enter normal mode
    if (!mcp2515_set_mode(MODE_NORMAL)) {
        ESP_LOGE(TAG, "Failed to enter normal mode");
        return ESP_FAIL;
    }

    ready = true;
    ESP_LOGI(TAG, "CAN bus initialized (MCP2515, %lu bps)", (unsigned long)config->bitrate);
    return ESP_OK;
}

esp_err_t canbus_send(const can_frame_t *frame)
{
    if (!ready || !frame) return ESP_ERR_INVALID_STATE;
    if (frame->dlc > CAN_MAX_DATA_LEN) return ESP_ERR_INVALID_ARG;

    // Wait for TX buffer free
    int retries = 10;
    while (retries-- > 0) {
        uint8_t ctrl = mcp2515_read_reg(MCP_TXB0CTRL);
        if (!(ctrl & 0x08)) break;  // TXREQ bit clear = buffer free
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    if (retries < 0) {
        ESP_LOGW(TAG, "TX buffer busy");
        return ESP_ERR_TIMEOUT;
    }

    // Hold SPI mutex for entire TX buffer load to prevent interleaving
    xSemaphoreTake(spi_mutex, portMAX_DELAY);

    // Load ID (using raw SPI without per-call mutex)
    if (frame->extended) {
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH, (frame->id >> 21) & 0xFF);
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH + 1,
            ((frame->id >> 13) & 0xE0) | 0x08 | ((frame->id >> 16) & 0x03));
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH + 2, (frame->id >> 8) & 0xFF);
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH + 3, frame->id & 0xFF);
    } else {
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH, (frame->id >> 3) & 0xFF);
        mcp2515_write_reg_unlocked(MCP_TXB0SIDH + 1, ((frame->id & 0x07) << 5));
    }

    // Load DLC + RTR
    uint8_t dlc_reg = frame->dlc & 0x0F;
    if (frame->rtr) dlc_reg |= 0x40;
    mcp2515_write_reg_unlocked(MCP_TXB0DLC, dlc_reg);

    // Load data
    for (uint8_t i = 0; i < frame->dlc; i++) {
        mcp2515_write_reg_unlocked(MCP_TXB0D0 + i, frame->data[i]);
    }

    // Request to send
    uint8_t tx[1] = { MCP_RTS_TXB0 };
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = tx,
    };
    spi_device_polling_transmit(spi_dev, &t);

    xSemaphoreGive(spi_mutex);

    return ESP_OK;
}

void canbus_set_recv_callback(can_recv_callback_t cb)
{
    recv_callback = cb;
}

esp_err_t canbus_set_filter(uint32_t mask, uint32_t filter)
{
    if (!ready) return ESP_ERR_INVALID_STATE;

    // Must be in config mode to change filters
    mcp2515_set_mode(MODE_CONFIG);

    mcp2515_write_reg(MCP_RXM0SIDH, (mask >> 3) & 0xFF);
    mcp2515_write_reg(MCP_RXM0SIDH + 1, ((mask & 0x07) << 5));
    mcp2515_write_reg(MCP_RXF0SIDH, (filter >> 3) & 0xFF);
    mcp2515_write_reg(MCP_RXF0SIDH + 1, ((filter & 0x07) << 5));

    mcp2515_set_mode(MODE_NORMAL);
    return ESP_OK;
}

esp_err_t canbus_set_bitrate(uint32_t bitrate)
{
    if (!ready) return ESP_ERR_INVALID_STATE;

    mcp2515_set_mode(MODE_CONFIG);
    esp_err_t ret = mcp2515_set_bitrate(bitrate);
    mcp2515_set_mode(MODE_NORMAL);
    return ret;
}

bool canbus_is_ready(void)
{
    return ready;
}

void canbus_task(void *params)
{
    can_frame_t frame;

    while (1) {
        // Poll INT pin (active low)
        if (gpio_get_level(current_config.pin_int) == 0) {
            uint8_t intf = mcp2515_read_reg(MCP_CANINTF);

            if (intf & CANINTF_RX0IF) {
                // Read received frame
                memset(&frame, 0, sizeof(frame));

                uint8_t sidh = mcp2515_read_reg(MCP_RXB0SIDH);
                uint8_t sidl = mcp2515_read_reg(MCP_RXB0SIDH + 1);

                if (sidl & 0x08) {
                    // Extended frame
                    frame.extended = true;
                    uint8_t eid8 = mcp2515_read_reg(MCP_RXB0SIDH + 2);
                    uint8_t eid0 = mcp2515_read_reg(MCP_RXB0SIDH + 3);
                    frame.id = ((uint32_t)sidh << 21) |
                               ((uint32_t)(sidl & 0xE0) << 13) |
                               ((uint32_t)(sidl & 0x03) << 16) |
                               ((uint32_t)eid8 << 8) |
                               (uint32_t)eid0;
                } else {
                    frame.id = ((uint32_t)sidh << 3) | ((sidl >> 5) & 0x07);
                }

                uint8_t dlc_reg = mcp2515_read_reg(MCP_RXB0DLC);
                frame.rtr = (dlc_reg & 0x40) != 0;
                frame.dlc = dlc_reg & 0x0F;
                if (frame.dlc > CAN_MAX_DATA_LEN) frame.dlc = CAN_MAX_DATA_LEN;

                for (uint8_t i = 0; i < frame.dlc; i++) {
                    frame.data[i] = mcp2515_read_reg(MCP_RXB0D0 + i);
                }

                // Clear RX flag
                mcp2515_bit_modify(MCP_CANINTF, CANINTF_RX0IF, 0x00);

                if (recv_callback) {
                    recv_callback(&frame);
                }
            }

            if (intf & CANINTF_ERRIF) {
                uint8_t eflg = mcp2515_read_reg(MCP_EFLG);
                if (eflg & EFLG_TXBO) {
                    ESP_LOGE(TAG, "CAN bus-off detected — initiating recovery");
                    mcp2515_set_mode(MODE_CONFIG);
                    mcp2515_write_reg(MCP_EFLG, 0x00);
                    mcp2515_write_reg(MCP_TEC, 0x00);
                    mcp2515_set_mode(MODE_NORMAL);
                } else {
                    ESP_LOGW(TAG, "CAN error (EFLG=0x%02X)", eflg);
                }
                mcp2515_bit_modify(MCP_CANINTF, CANINTF_ERRIF, 0x00);
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
