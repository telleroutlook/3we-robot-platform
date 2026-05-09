// SPDX-License-Identifier: Apache-2.0
// Unity Test Framework — Minimal implementation for host-side firmware tests
// Based on ThrowTheSwitch/Unity (MIT License)
// Full version: https://github.com/ThrowTheSwitch/Unity
#ifndef UNITY_H
#define UNITY_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

int unity_begin(const char *file);
void unity_test_start(const char *name);
void unity_test_end(void);
void unity_fail(const char *file, int line, const char *msg);
int unity_end(void);

#define UNITY_BEGIN() unity_begin(__FILE__)
#define UNITY_END()   unity_end()

#define RUN_TEST(func) do { \
    unity_test_start(#func); \
    func(); \
    unity_test_end(); \
} while(0)

#define TEST_ASSERT_TRUE(cond) do { \
    if (!(cond)) unity_fail(__FILE__, __LINE__, "Expected TRUE"); \
} while(0)

#define TEST_ASSERT_FALSE(cond) do { \
    if (cond) unity_fail(__FILE__, __LINE__, "Expected FALSE"); \
} while(0)

#define TEST_ASSERT_EQUAL(expected, actual) do { \
    if ((expected) != (actual)) { \
        char _msg[128]; \
        snprintf(_msg, sizeof(_msg), "Expected %d, got %d", (int)(expected), (int)(actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#define TEST_ASSERT_EQUAL_INT32(expected, actual) do { \
    if ((int32_t)(expected) != (int32_t)(actual)) { \
        char _msg[128]; \
        snprintf(_msg, sizeof(_msg), "Expected %d, got %d", (int)(expected), (int)(actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#define TEST_ASSERT_EQUAL_UINT8(expected, actual) do { \
    if ((uint8_t)(expected) != (uint8_t)(actual)) { \
        char _msg[128]; \
        snprintf(_msg, sizeof(_msg), "Expected %u, got %u", (unsigned)(uint8_t)(expected), (unsigned)(uint8_t)(actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#define TEST_ASSERT_UINT8_WITHIN(delta, expected, actual) do { \
    int _diff = abs((int)(uint8_t)(expected) - (int)(uint8_t)(actual)); \
    if (_diff > (int)(delta)) { \
        char _msg[128]; \
        snprintf(_msg, sizeof(_msg), "Expected %u +/- %u, got %u", \
            (unsigned)(uint8_t)(expected), (unsigned)(delta), (unsigned)(uint8_t)(actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#define TEST_ASSERT_FLOAT_WITHIN(delta, expected, actual) do { \
    float _diff = fabsf((float)(expected) - (float)(actual)); \
    if (_diff > (float)(delta)) { \
        char _msg[128]; \
        snprintf(_msg, sizeof(_msg), "Expected %.6f +/- %.6f, got %.6f", \
            (double)(expected), (double)(delta), (double)(actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#define TEST_ASSERT_NOT_NULL(ptr) do { \
    if ((ptr) == NULL) unity_fail(__FILE__, __LINE__, "Expected non-NULL"); \
} while(0)

#define TEST_ASSERT_NULL(ptr) do { \
    if ((ptr) != NULL) unity_fail(__FILE__, __LINE__, "Expected NULL"); \
} while(0)

#define TEST_ASSERT_EQUAL_STRING(expected, actual) do { \
    if (strcmp((expected), (actual)) != 0) { \
        char _msg[256]; \
        snprintf(_msg, sizeof(_msg), "Expected \"%s\", got \"%s\"", (expected), (actual)); \
        unity_fail(__FILE__, __LINE__, _msg); \
    } \
} while(0)

#endif // UNITY_H
