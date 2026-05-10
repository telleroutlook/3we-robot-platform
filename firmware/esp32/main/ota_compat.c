// SPDX-License-Identifier: Apache-2.0
#include "ota_compat.h"
#include "ota_signing.h"

#include "esp_log.h"

static const char *TAG = "ota_compat";

// Protocol version compatibility matrix.
// Firmware versions are packed as (major << 16 | minor << 8 | patch).
// "2.1.0" = 0x00020100.
static const ota_compat_entry_t s_compat_table[] = {
    // V1.x.x used old UDP protocol (incompatible)
    { .fw_version_min = 0x00010000, .fw_version_max = 0x0001FFFF, .protocol_version = 1 },
    // V2.x.x uses micro-ROS UART + DTLS
    { .fw_version_min = 0x00020000, .fw_version_max = 0x0002FFFF, .protocol_version = 2 },
    // V3.x.x maintains protocol V2 (backward compatible)
    { .fw_version_min = 0x00030000, .fw_version_max = 0x0003FFFF, .protocol_version = 2 },
};

#define COMPAT_TABLE_SIZE (sizeof(s_compat_table) / sizeof(s_compat_table[0]))

static uint8_t get_protocol_for_version(uint32_t version)
{
    for (size_t i = 0; i < COMPAT_TABLE_SIZE; i++) {
        if (version >= s_compat_table[i].fw_version_min &&
            version <= s_compat_table[i].fw_version_max) {
            return s_compat_table[i].protocol_version;
        }
    }
    return 0; // Unknown version
}

bool ota_check_compatibility(uint32_t new_version)
{
    uint32_t current = ota_get_current_version();
    if (current == UINT32_MAX) {
        // No current version info — allow update
        return true;
    }

    uint8_t current_proto = get_protocol_for_version(current);
    uint8_t new_proto = get_protocol_for_version(new_version);

    if (new_proto == 0) {
        ESP_LOGW(TAG, "Unknown protocol for version 0x%08lX", (unsigned long)new_version);
        return false;
    }

    if (current_proto != 0 && new_proto != current_proto) {
        ESP_LOGE(TAG, "Protocol mismatch: current=V%d, new=V%d (version 0x%08lX)",
                 current_proto, new_proto, (unsigned long)new_version);
        return false;
    }

    return true;
}
