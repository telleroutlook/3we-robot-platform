// SPDX-License-Identifier: Apache-2.0
// Unit tests for DTLS authority state machine (dtls_authority.c)
#include "unity.h"
#include "dtls_authority.h"

static dtls_authority_t auth;

void setUp_authority(void) {
    authority_init(&auth);
}

// --- authority_init ---

void test_authority_init_sets_no_holder(void) {
    setUp_authority();
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
}

void test_authority_init_no_one_is_holder(void) {
    setUp_authority();
    TEST_ASSERT_FALSE(authority_is_holder(&auth, 0));
    TEST_ASSERT_FALSE(authority_is_holder(&auth, 1));
    TEST_ASSERT_FALSE(authority_is_holder(&auth, 3));
}

// --- authority_request: grant when empty ---

void test_authority_request_grants_when_empty(void) {
    setUp_authority();
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 0, 10, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_GRANTED, r);
    TEST_ASSERT_EQUAL(-1, preempted);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
    TEST_ASSERT_TRUE(authority_is_holder(&auth, 0));
}

void test_authority_request_grants_different_session_when_empty(void) {
    setUp_authority();
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 2, 50, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_GRANTED, r);
    TEST_ASSERT_EQUAL(2, authority_get_holder(&auth));
}

// --- authority_request: same session re-request ---

void test_authority_request_same_session_returns_granted(void) {
    setUp_authority();
    authority_request(&auth, 1, 20, NULL);
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 1, 20, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_GRANTED, r);
    TEST_ASSERT_EQUAL(-1, preempted);
    TEST_ASSERT_EQUAL(1, authority_get_holder(&auth));
}

// --- authority_request: preemption by higher priority ---

void test_authority_request_preempts_lower_priority(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 1, 20, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_PREEMPTED, r);
    TEST_ASSERT_EQUAL(0, preempted);
    TEST_ASSERT_EQUAL(1, authority_get_holder(&auth));
    TEST_ASSERT_FALSE(authority_is_holder(&auth, 0));
}

// --- authority_request: denial by equal priority ---

void test_authority_request_denied_equal_priority(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 1, 10, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_DENIED, r);
    TEST_ASSERT_EQUAL(-1, preempted);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
}

// --- authority_request: denial by lower priority ---

void test_authority_request_denied_lower_priority(void) {
    setUp_authority();
    authority_request(&auth, 0, 50, NULL);
    int8_t preempted = -1;
    authority_result_t r = authority_request(&auth, 2, 30, &preempted);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_DENIED, r);
    TEST_ASSERT_EQUAL(-1, preempted);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
}

// --- authority_request: invalid session ---

void test_authority_request_rejects_invalid_session(void) {
    setUp_authority();
    authority_result_t r = authority_request(&auth, DTLS_MAX_SESSIONS, 100, NULL);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_DENIED, r);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
}

// --- authority_request: null preempted pointer ---

void test_authority_request_null_preempted_does_not_crash(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_result_t r = authority_request(&auth, 1, 20, NULL);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_PREEMPTED, r);
    TEST_ASSERT_EQUAL(1, authority_get_holder(&auth));
}

// --- authority_release ---

void test_authority_release_clears_holder(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_release(&auth, 0);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
    TEST_ASSERT_FALSE(authority_is_holder(&auth, 0));
}

void test_authority_release_wrong_session_no_effect(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_release(&auth, 1);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
}

void test_authority_release_when_empty_no_effect(void) {
    setUp_authority();
    authority_release(&auth, 0);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
}

// --- authority_session_disconnected ---

void test_authority_disconnect_releases_holder(void) {
    setUp_authority();
    authority_request(&auth, 2, 50, NULL);
    authority_session_disconnected(&auth, 2);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
}

void test_authority_disconnect_non_holder_no_effect(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_session_disconnected(&auth, 1);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
}

// --- authority_feed ---

void test_authority_feed_updates_timestamp(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_feed(&auth, 1000000);
    TEST_ASSERT_EQUAL(1000000, auth.last_cmd_us);
}

void test_authority_feed_no_holder_is_noop(void) {
    setUp_authority();
    authority_feed(&auth, 1000000);
    TEST_ASSERT_EQUAL(0, auth.last_cmd_us);
}

// --- authority_check_idle ---

void test_authority_check_idle_no_holder_returns_false(void) {
    setUp_authority();
    TEST_ASSERT_FALSE(authority_check_idle(&auth, 5000000, 1000000));
}

void test_authority_check_idle_no_feed_yet_returns_false(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    TEST_ASSERT_FALSE(authority_check_idle(&auth, 5000000, 1000000));
}

void test_authority_check_idle_within_timeout_returns_false(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_feed(&auth, 1000000);
    TEST_ASSERT_FALSE(authority_check_idle(&auth, 1500000, 1000000));
}

void test_authority_check_idle_expired_releases_and_returns_true(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_feed(&auth, 1000000);
    bool expired = authority_check_idle(&auth, 2500000, 1000000);
    TEST_ASSERT_TRUE(expired);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
}

void test_authority_check_idle_exact_boundary_not_expired(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_feed(&auth, 1000000);
    TEST_ASSERT_FALSE(authority_check_idle(&auth, 2000000, 1000000));
}

// --- Sequence: preemption then re-request after release ---

void test_authority_sequence_preempt_release_rerequest(void) {
    setUp_authority();
    authority_request(&auth, 0, 10, NULL);
    authority_request(&auth, 1, 20, NULL);
    TEST_ASSERT_EQUAL(1, authority_get_holder(&auth));
    authority_release(&auth, 1);
    TEST_ASSERT_EQUAL(-1, authority_get_holder(&auth));
    authority_result_t r = authority_request(&auth, 0, 10, NULL);
    TEST_ASSERT_EQUAL(AUTHORITY_RESULT_GRANTED, r);
    TEST_ASSERT_EQUAL(0, authority_get_holder(&auth));
}
