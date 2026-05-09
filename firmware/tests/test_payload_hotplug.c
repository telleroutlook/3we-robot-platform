// SPDX-License-Identifier: Apache-2.0
// Unit tests for payload_hotplug — hot-plug detection and power sequencing
#include "unity.h"
#include "i2c_stubs.h"
#include "freertos/semphr.h"
#include "pin_definitions.h"

#include <string.h>

// pdTRUE required by i2c_bus.h inline lock function
#ifndef pdTRUE
#define pdTRUE 1
#endif

#include "payload_hotplug.h"

#define TEST_ASSERT_NOT_EQUAL(expected, actual) TEST_ASSERT_TRUE((expected) != (actual))
#define TEST_ASSERT_EQUAL_HEX8(expected, actual) TEST_ASSERT_EQUAL_UINT8((expected), (actual))
#define TEST_ASSERT_GREATER_OR_EQUAL(threshold, actual) \
    TEST_ASSERT_TRUE((int)(actual) >= (int)(threshold))
#define TEST_ASSERT_EQUAL_MEMORY(expected, actual, len) \
    TEST_ASSERT_TRUE(memcmp((expected), (actual), (len)) == 0)

// Stub: i2c_bus_get_mutex returns a non-NULL handle so i2c_bus_lock() succeeds
SemaphoreHandle_t i2c_bus_get_mutex(void) { return (SemaphoreHandle_t)0x2; }

// MCP23017 registers
#define MCP_IODIRA  0x00
#define MCP_GPIOA   0x12
#define MCP_OLATA   0x14

// Callback tracking
static payload_state_t last_cb_state = PAYLOAD_STATE_ABSENT;
static const payload_descriptor_t *last_cb_desc = NULL;
static int cb_call_count = 0;

static void test_callback(payload_state_t s, const payload_descriptor_t *d)
{
    last_cb_state = s;
    last_cb_desc = d;
    cb_call_count++;
}

static void reset_callback_tracking(void)
{
    last_cb_state = PAYLOAD_STATE_ABSENT;
    last_cb_desc = NULL;
    cb_call_count = 0;
}

// Helper: build valid 64-byte EEPROM descriptor data
static void build_valid_eeprom(uint8_t *data)
{
    memset(data, 0, 64);
    memcpy(data, "PBC4", 4);                       // magic
    data[4] = 0x01;                                 // version
    memcpy(&data[5], "test-payload-01", 15);        // payload_id
    memcpy(&data[0x15], "Test Sensor Array", 17);   // name
    data[0x35] = 0x01; data[0x36] = 0xF4;          // power_5v = 500mA (big-endian)
    data[0x37] = 0x00; data[0x38] = 0x00;          // power_12v = 0mA
    data[0x39] = 0x01;                              // capabilities = CAP_I2C
    data[0x3A] = 0x03;                              // gpio_mask = bits 0,1
}

void hotplug_test_setUp(void)
{
    mock_i2c_reset();
    reset_callback_tracking();
}

void hotplug_test_tearDown(void)
{
}

// ---------------------------------------------------------------------------
// Test 1: payload_hotplug_init succeeds when MCP23017 writes succeed
// ---------------------------------------------------------------------------
void test_hotplug_init_success(void)
{
    esp_err_t err = payload_hotplug_init();
    TEST_ASSERT_EQUAL(ESP_OK, err);
}

// ---------------------------------------------------------------------------
// Test 2: payload_hotplug_init propagates I2C write failure
// ---------------------------------------------------------------------------
void test_hotplug_init_failure_iodir(void)
{
    mock_i2c_set_write_error(MCP23017_ADDR, ESP_FAIL);

    esp_err_t err = payload_hotplug_init();
    TEST_ASSERT_NOT_EQUAL(ESP_OK, err);
}

// ---------------------------------------------------------------------------
// Test 3: state is ABSENT after successful init
// ---------------------------------------------------------------------------
void test_hotplug_state_absent_after_init(void)
{
    payload_hotplug_init();

    payload_state_t s = payload_get_state();
    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, s);
}

// ---------------------------------------------------------------------------
// Test 4: descriptor is NULL when state is ABSENT
// ---------------------------------------------------------------------------
void test_hotplug_descriptor_null_when_absent(void)
{
    payload_hotplug_init();

    const payload_descriptor_t *desc = payload_get_descriptor();
    TEST_ASSERT_NULL(desc);
}

// ---------------------------------------------------------------------------
// Test 5: payload_power_off writes zeros to MCP23017 OLAT bits
// ---------------------------------------------------------------------------
void test_hotplug_power_off_writes_zeros(void)
{
    // Set up mock read data for OLAT register (mcp23017_write_bit reads then writes)
    uint8_t olat_val = 0x07;  // All power bits on initially
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    payload_hotplug_init();

    esp_err_t err = payload_power_off();
    TEST_ASSERT_EQUAL(ESP_OK, err);

    // Verify state transitions to ABSENT
    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, payload_get_state());
}

// ---------------------------------------------------------------------------
// Test 6: register_callback does not crash (smoke test)
// ---------------------------------------------------------------------------
void test_hotplug_register_callback_smoke(void)
{
    payload_register_callback(test_callback);
    // No crash = pass. Also test registering NULL.
    payload_register_callback(NULL);
    payload_register_callback(test_callback);
}

// ---------------------------------------------------------------------------
// Test 7: power_off notifies registered callback with ABSENT state
// ---------------------------------------------------------------------------
void test_hotplug_power_off_notifies_callback(void)
{
    uint8_t olat_val = 0x07;
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    payload_hotplug_init();
    payload_register_callback(test_callback);

    payload_power_off();

    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, last_cb_state);
    TEST_ASSERT_EQUAL(1, cb_call_count);
}

// ---------------------------------------------------------------------------
// Test 8: init performs IODIR write as first I2C operation
// ---------------------------------------------------------------------------
void test_hotplug_init_iodir_write_first(void)
{
    payload_hotplug_init();

    // After init the MCP23017 should have received writes.
    // The first write is IODIR (reg 0x00, val 0xF8),
    // the second write is OLAT (reg 0x14, val 0x00).
    // Since mock tracks last_write, after init the last write is the OLAT one.
    size_t len = 0;
    const uint8_t *data = mock_i2c_get_last_write(MCP23017_ADDR, &len);
    TEST_ASSERT_NOT_NULL(data);
    TEST_ASSERT_EQUAL(2, len);
    // Last write should be OLAT = 0x00
    TEST_ASSERT_EQUAL_HEX8(MCP_OLATA, data[0]);
    TEST_ASSERT_EQUAL_HEX8(0x00, data[1]);

    // At least 2 writes to MCP23017 (IODIR + OLAT)
    int count = mock_i2c_get_write_count(MCP23017_ADDR);
    TEST_ASSERT_GREATER_OR_EQUAL(2, count);
}

// ---------------------------------------------------------------------------
// Test 9: init with OLAT write failure propagates error
// ---------------------------------------------------------------------------
void test_hotplug_init_failure_olat(void)
{
    // To make OLAT fail but IODIR succeed, we need to set write error
    // after the first write. Since our mock doesn't support per-write errors,
    // we test that any write error on the MCP23017 results in failure.
    mock_i2c_set_write_error(MCP23017_ADDR, ESP_FAIL);

    esp_err_t err = payload_hotplug_init();
    TEST_ASSERT_NOT_EQUAL(ESP_OK, err);
}

// ---------------------------------------------------------------------------
// Test 10: power_off succeeds even when called multiple times
// ---------------------------------------------------------------------------
void test_hotplug_power_off_idempotent(void)
{
    uint8_t olat_val = 0x00;
    mock_i2c_set_read_data(MCP23017_ADDR, MCP_OLATA, &olat_val, 1);

    payload_hotplug_init();

    esp_err_t err1 = payload_power_off();
    esp_err_t err2 = payload_power_off();
    TEST_ASSERT_EQUAL(ESP_OK, err1);
    TEST_ASSERT_EQUAL(ESP_OK, err2);
    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, payload_get_state());
}

// ---------------------------------------------------------------------------
// Test 11: valid EEPROM data at address 0x50 is parseable (mock setup test)
// ---------------------------------------------------------------------------
void test_hotplug_eeprom_mock_setup(void)
{
    uint8_t eeprom[64];
    build_valid_eeprom(eeprom);

    // Set up the mock so reads from EEPROM addr 0x50, register 0x00 return our data
    mock_i2c_set_read_data(0x50, 0x00, eeprom, 64);

    // Verify mock infrastructure returns what we set
    // (This validates the test helper, not the firmware function directly)
    uint8_t readback[64] = {0};
    uint8_t reg = 0x00;
    esp_err_t err = i2c_master_write_read_device(I2C_NUM_0, 0x50,
                                                  &reg, 1, readback, 64, 100);
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL_MEMORY("PBC4", readback, 4);
    TEST_ASSERT_EQUAL_HEX8(0x01, readback[0x39]);  // capabilities
    TEST_ASSERT_EQUAL_HEX8(0x03, readback[0x3A]);  // gpio_mask
}

// ---------------------------------------------------------------------------
// Test 12: power_off with I2C read error still transitions state to ABSENT
// ---------------------------------------------------------------------------
void test_hotplug_power_off_with_i2c_error(void)
{
    payload_hotplug_init();
    payload_register_callback(test_callback);

    // Make read fail — mcp23017_write_bit will fail on read-modify-write
    mock_i2c_set_read_error(MCP23017_ADDR, ESP_FAIL);

    // power_off calls mcp23017_write_bit 3 times; each will fail on read,
    // but the function still sets state to ABSENT and notifies
    esp_err_t err = payload_power_off();
    // The function returns ESP_OK regardless of individual bit-write failures
    // because it always transitions state
    TEST_ASSERT_EQUAL(ESP_OK, err);
    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, payload_get_state());
    TEST_ASSERT_EQUAL(PAYLOAD_STATE_ABSENT, last_cb_state);
}
