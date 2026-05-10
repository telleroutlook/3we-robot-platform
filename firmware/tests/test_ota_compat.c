// SPDX-License-Identifier: Apache-2.0
#include "unity.h"
#include "ota_compat.h"
#include "ota_signing.h"

#include <stdint.h>

// Declared in mbedtls_stubs.h
extern void mock_ota_set_current_version(const char *version);

void test_compat_same_protocol_version_passes(void)
{
    mock_ota_set_current_version("2.1.0"); // V2 protocol → 0x00020100
    // V2.2.0 = 0x00020200, same protocol
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00020200));
}

void test_compat_v3_compatible_with_v2(void)
{
    mock_ota_set_current_version("2.1.0");
    // V3.0.0 = 0x00030000, uses protocol V2 (backward compatible per compat table)
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00030000));
}

void test_compat_v1_incompatible_with_v2(void)
{
    mock_ota_set_current_version("2.1.0");
    // V1.5.0 = 0x00010500, uses protocol V1 (incompatible with current V2)
    TEST_ASSERT_FALSE(ota_check_compatibility(0x00010500));
}

void test_compat_unknown_version_rejected(void)
{
    mock_ota_set_current_version("2.1.0");
    // V4.0.0 = 0x00040000, not in compat table
    TEST_ASSERT_FALSE(ota_check_compatibility(0x00040000));
}

void test_compat_no_current_version_allows_any(void)
{
    mock_ota_set_current_version("invalid"); // Returns UINT32_MAX
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00010000));
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00020000));
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00030000));
}

void test_compat_v2_min_boundary(void)
{
    mock_ota_set_current_version("2.0.0"); // V2 minimum = 0x00020000
    TEST_ASSERT_TRUE(ota_check_compatibility(0x0002FFFF)); // still V2
}

void test_compat_v2_max_boundary(void)
{
    mock_ota_set_current_version("2.255.255"); // V2 max = 0x0002FFFF
    TEST_ASSERT_TRUE(ota_check_compatibility(0x00020000)); // V2 min
}
