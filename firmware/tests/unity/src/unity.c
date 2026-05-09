// SPDX-License-Identifier: Apache-2.0
// Unity — implementation for shared state across translation units
#include "unity.h"

static int _unity_tests_run = 0;
static int _unity_tests_failed = 0;
static int _unity_current_failed = 0;
static const char *_unity_current_test = NULL;

int unity_begin(const char *file) {
    printf("\n--- Unit Tests: %s ---\n", file);
    _unity_tests_run = 0;
    _unity_tests_failed = 0;
    return 0;
}

void unity_test_start(const char *name) {
    _unity_current_test = name;
    _unity_current_failed = 0;
    _unity_tests_run++;
}

void unity_test_end(void) {
    if (_unity_current_failed == 0) {
        printf("  PASS: %s\n", _unity_current_test);
    }
}

void unity_fail(const char *file, int line, const char *msg) {
    if (_unity_current_failed == 0) {
        _unity_tests_failed++;
        _unity_current_failed = 1;
    }
    printf("  FAIL: %s\n", _unity_current_test ? _unity_current_test : "(unknown)");
    printf("        %s:%d: %s\n", file, line, msg);
}

int unity_end(void) {
    printf("\n--- Results: %d tests, %d passed, %d failed ---\n",
           _unity_tests_run, _unity_tests_run - _unity_tests_failed, _unity_tests_failed);
    return (_unity_tests_failed > 0) ? 1 : 0;
}
