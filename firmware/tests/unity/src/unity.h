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

// Internal state
static int _unity_tests_run = 0;
static int _unity_tests_failed = 0;
static int _unity_current_failed = 0;
static const char *_unity_current_test = NULL;

static inline int unity_begin(const char *file) {
    printf("\n--- Unit Tests: %s ---\n", file);
    _unity_tests_run = 0;
    _unity_tests_failed = 0;
    return 0;
}

static inline void unity_test_start(const char *name) {
    _unity_current_test = name;
    _unity_current_failed = 0;
    _unity_tests_run++;
}

static inline void unity_test_end(void) {
    if (_unity_current_failed == 0) {
        printf("  PASS: %s\n", _unity_current_test);
    }
}

static inline void unity_fail(const char *file, int line, const char *msg) {
    if (_unity_current_failed == 0) {
        _unity_tests_failed++;
        _unity_current_failed = 1;
    }
    printf("  FAIL: %s\n", _unity_current_test);
    printf("        %s:%d: %s\n", file, line, msg);
}

static inline int unity_end(void) {
    printf("\n--- Results: %d tests, %d passed, %d failed ---\n",
           _unity_tests_run, _unity_tests_run - _unity_tests_failed, _unity_tests_failed);
    return (_unity_tests_failed > 0) ? 1 : 0;
}

#endif // UNITY_H
