// SPDX-License-Identifier: Apache-2.0
#ifndef DTLS_AUTHORITY_H
#define DTLS_AUTHORITY_H

#include <stdint.h>
#include <stdbool.h>

#define DTLS_MAX_SESSIONS   4

typedef enum {
    DTLS_ROLE_OBSERVER = 0,
    DTLS_ROLE_OPERATOR,
} dtls_role_t;

typedef struct {
    int8_t   holder_idx;
    uint8_t  holder_priority;
    int64_t  last_cmd_us;
} dtls_authority_t;

typedef enum {
    AUTHORITY_RESULT_GRANTED = 0,
    AUTHORITY_RESULT_DENIED,
    AUTHORITY_RESULT_PREEMPTED,
} authority_result_t;

void authority_init(dtls_authority_t *auth);

authority_result_t authority_request(dtls_authority_t *auth,
                                    uint8_t session_idx, uint8_t priority,
                                    int8_t *preempted_idx);

void authority_release(dtls_authority_t *auth, uint8_t session_idx);

void authority_session_disconnected(dtls_authority_t *auth, uint8_t session_idx);

bool authority_is_holder(const dtls_authority_t *auth, uint8_t session_idx);

int8_t authority_get_holder(const dtls_authority_t *auth);

void authority_feed(dtls_authority_t *auth, int64_t now_us);

bool authority_check_idle(dtls_authority_t *auth, int64_t now_us,
                          uint32_t idle_timeout_us);

#endif // DTLS_AUTHORITY_H
