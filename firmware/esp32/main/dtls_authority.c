// SPDX-License-Identifier: Apache-2.0
#include "dtls_authority.h"

void authority_init(dtls_authority_t *auth)
{
    auth->holder_idx = -1;
    auth->holder_priority = 0;
    auth->last_cmd_us = 0;
}

authority_result_t authority_request(dtls_authority_t *auth,
                                    uint8_t session_idx, uint8_t priority,
                                    int8_t *preempted_idx)
{
    if (preempted_idx) {
        *preempted_idx = -1;
    }

    if (session_idx >= DTLS_MAX_SESSIONS) {
        return AUTHORITY_RESULT_DENIED;
    }

    if (auth->holder_idx < 0) {
        auth->holder_idx = (int8_t)session_idx;
        auth->holder_priority = priority;
        auth->last_cmd_us = 0;
        return AUTHORITY_RESULT_GRANTED;
    }

    if (auth->holder_idx == (int8_t)session_idx) {
        return AUTHORITY_RESULT_GRANTED;
    }

    if (priority > auth->holder_priority) {
        if (preempted_idx) {
            *preempted_idx = auth->holder_idx;
        }
        auth->holder_idx = (int8_t)session_idx;
        auth->holder_priority = priority;
        auth->last_cmd_us = 0;
        return AUTHORITY_RESULT_PREEMPTED;
    }

    return AUTHORITY_RESULT_DENIED;
}

void authority_release(dtls_authority_t *auth, uint8_t session_idx)
{
    if (auth->holder_idx == (int8_t)session_idx) {
        auth->holder_idx = -1;
        auth->holder_priority = 0;
        auth->last_cmd_us = 0;
    }
}

void authority_session_disconnected(dtls_authority_t *auth, uint8_t session_idx)
{
    authority_release(auth, session_idx);
}

bool authority_is_holder(const dtls_authority_t *auth, uint8_t session_idx)
{
    return auth->holder_idx == (int8_t)session_idx;
}

int8_t authority_get_holder(const dtls_authority_t *auth)
{
    return auth->holder_idx;
}

void authority_feed(dtls_authority_t *auth, int64_t now_us)
{
    if (auth->holder_idx >= 0) {
        auth->last_cmd_us = now_us;
    }
}

bool authority_check_idle(dtls_authority_t *auth, int64_t now_us,
                          uint32_t idle_timeout_us)
{
    if (auth->holder_idx < 0) {
        return false;
    }

    if (auth->last_cmd_us == 0) {
        return false;
    }

    int64_t elapsed = now_us - auth->last_cmd_us;
    if (elapsed > (int64_t)idle_timeout_us) {
        auth->holder_idx = -1;
        auth->holder_priority = 0;
        auth->last_cmd_us = 0;
        return true;
    }

    return false;
}
