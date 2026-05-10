// SPDX-License-Identifier: Apache-2.0
#ifndef OTA_COMPAT_H
#define OTA_COMPAT_H

#include <stdint.h>
#include <stdbool.h>

#define OTA_PROTOCOL_VERSION_CURRENT  2

typedef struct {
    uint32_t fw_version_min;
    uint32_t fw_version_max;
    uint8_t  protocol_version;
} ota_compat_entry_t;

bool ota_check_compatibility(uint32_t new_version);

#endif // OTA_COMPAT_H
