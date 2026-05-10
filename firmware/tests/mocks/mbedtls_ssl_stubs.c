// SPDX-License-Identifier: Apache-2.0
// Mock implementations for mbedtls SSL/networking functions
#include "mbedtls_ssl_stubs.h"
#include <string.h>

// --- Configurable mock state ---
static int mock_handshake_result = 0;
static int mock_read_result = MBEDTLS_ERR_SSL_WANT_READ;
static const unsigned char *mock_read_data = NULL;
static size_t mock_read_data_len = 0;
static size_t mock_read_data_offset = 0;
static int mock_psk_cb_capture = 0;
static int mock_psk_cb_called = 0;
static int mock_accept_max_calls = 1;
static int mock_accept_call_count = 0;

// PSK callback pointer captured from conf_psk_cb
static int (*captured_psk_cb)(void *, mbedtls_ssl_context *, const unsigned char *, size_t) = NULL;
static void *captured_psk_cb_param = NULL;

void mock_ssl_reset(void) {
    mock_handshake_result = 0;
    mock_read_result = MBEDTLS_ERR_SSL_WANT_READ;
    mock_read_data = NULL;
    mock_read_data_len = 0;
    mock_read_data_offset = 0;
    mock_psk_cb_capture = 0;
    mock_psk_cb_called = 0;
    mock_accept_max_calls = 1;
    mock_accept_call_count = 0;
    captured_psk_cb = NULL;
    captured_psk_cb_param = NULL;
}

void mock_ssl_set_handshake_result(int result) { mock_handshake_result = result; }

void mock_ssl_set_read_data(const unsigned char *data, size_t len) {
    mock_read_data = data;
    mock_read_data_len = len;
    mock_read_data_offset = 0;
    mock_read_result = 0;
}

void mock_ssl_set_read_result(int result) { mock_read_result = result; }
void mock_ssl_set_psk_cb_capture(int enable) { mock_psk_cb_capture = enable; }
int mock_ssl_get_psk_cb_called(void) { return mock_psk_cb_called; }
void mock_ssl_set_accept_max_calls(int max_calls) { mock_accept_max_calls = max_calls; }

void mbedtls_ssl_init(mbedtls_ssl_context *ssl) { memset(ssl, 0, sizeof(*ssl)); }
void mbedtls_ssl_config_init(mbedtls_ssl_config *conf) { memset(conf, 0, sizeof(*conf)); }
void mbedtls_entropy_init(mbedtls_entropy_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }
void mbedtls_ctr_drbg_init(mbedtls_ctr_drbg_context *ctx) { memset(ctx, 0, sizeof(*ctx)); }
void mbedtls_ssl_cookie_init(mbedtls_ssl_cookie_ctx *ctx) { memset(ctx, 0, sizeof(*ctx)); }
void mbedtls_net_init(mbedtls_net_context *ctx) { ctx->fd = -1; }

void mbedtls_ssl_free(mbedtls_ssl_context *ssl) { (void)ssl; }
void mbedtls_ssl_config_free(mbedtls_ssl_config *conf) { (void)conf; }
void mbedtls_entropy_free(mbedtls_entropy_context *ctx) { (void)ctx; }
void mbedtls_ctr_drbg_free(mbedtls_ctr_drbg_context *ctx) { (void)ctx; }
void mbedtls_ssl_cookie_free(mbedtls_ssl_cookie_ctx *ctx) { (void)ctx; }
void mbedtls_net_free(mbedtls_net_context *ctx) { ctx->fd = -1; }

int mbedtls_entropy_func(void *data, unsigned char *output, size_t len) {
    (void)data; memset(output, 0x42, len); return 0;
}
int mbedtls_ctr_drbg_random(void *p_rng, unsigned char *output, size_t output_len) {
    (void)p_rng; memset(output, 0x42, output_len); return 0;
}
int mbedtls_ctr_drbg_seed(mbedtls_ctr_drbg_context *ctx,
                            int (*f_entropy)(void *, unsigned char *, size_t),
                            void *p_entropy, const unsigned char *custom, size_t len) {
    (void)ctx; (void)f_entropy; (void)p_entropy; (void)custom; (void)len;
    return 0;
}

int mbedtls_ssl_config_defaults(mbedtls_ssl_config *conf, int endpoint, int transport, int preset) {
    (void)conf; (void)endpoint; (void)transport; (void)preset; return 0;
}
void mbedtls_ssl_conf_min_tls_version(mbedtls_ssl_config *conf, int ver) { (void)conf; (void)ver; }
void mbedtls_ssl_conf_rng(mbedtls_ssl_config *conf,
                           int (*f_rng)(void *, unsigned char *, size_t), void *p_rng) {
    (void)conf; (void)f_rng; (void)p_rng;
}
void mbedtls_ssl_conf_psk_cb(mbedtls_ssl_config *conf,
                              int (*f_psk)(void *, mbedtls_ssl_context *, const unsigned char *, size_t),
                              void *p_psk) {
    (void)conf;
    captured_psk_cb = f_psk;
    captured_psk_cb_param = p_psk;
}
int mbedtls_ssl_cookie_setup(mbedtls_ssl_cookie_ctx *ctx,
                              int (*f_rng)(void *, unsigned char *, size_t), void *p_rng) {
    (void)ctx; (void)f_rng; (void)p_rng; return 0;
}
int mbedtls_ssl_cookie_write(void *ctx, unsigned char **p, unsigned char *end,
                              const unsigned char *info, size_t ilen) {
    (void)ctx; (void)p; (void)end; (void)info; (void)ilen; return 0;
}
int mbedtls_ssl_cookie_check(void *ctx, const unsigned char *cookie, size_t clen,
                              const unsigned char *info, size_t ilen) {
    (void)ctx; (void)cookie; (void)clen; (void)info; (void)ilen; return 0;
}
void mbedtls_ssl_conf_dtls_cookies(mbedtls_ssl_config *conf,
                                    int (*f_cookie_write)(void *, unsigned char **, unsigned char *, const unsigned char *, size_t),
                                    int (*f_cookie_check)(void *, const unsigned char *, size_t, const unsigned char *, size_t),
                                    void *p_cookie) {
    (void)conf; (void)f_cookie_write; (void)f_cookie_check; (void)p_cookie;
}
void mbedtls_ssl_conf_handshake_timeout(mbedtls_ssl_config *conf, uint32_t min, uint32_t max) {
    (void)conf; (void)min; (void)max;
}
void mbedtls_ssl_conf_read_timeout(mbedtls_ssl_config *conf, uint32_t timeout) {
    (void)conf; (void)timeout;
}
void mbedtls_ssl_conf_ciphersuites(mbedtls_ssl_config *conf, const int *ciphersuites) {
    (void)conf; (void)ciphersuites;
}
int mbedtls_ssl_setup(mbedtls_ssl_context *ssl, const mbedtls_ssl_config *conf) {
    (void)ssl; (void)conf; return 0;
}
void mbedtls_ssl_set_timer_cb(mbedtls_ssl_context *ssl, void *p_timer,
                               void (*f_set_timer)(void *, uint32_t, uint32_t),
                               int (*f_get_timer)(void *)) {
    (void)ssl; (void)p_timer; (void)f_set_timer; (void)f_get_timer;
}
void mbedtls_timing_set_delay(void *data, uint32_t int_ms, uint32_t fin_ms) {
    (void)data; (void)int_ms; (void)fin_ms;
}
int mbedtls_timing_get_delay(void *data) { (void)data; return 0; }

int mbedtls_net_bind(mbedtls_net_context *ctx, const char *bind_ip, const char *port, int proto) {
    (void)bind_ip; (void)port; (void)proto;
    ctx->fd = 42;
    return 0;
}
int mbedtls_net_accept(mbedtls_net_context *bind_ctx, mbedtls_net_context *client_ctx,
                        void *client_ip, size_t buf_size, size_t *ip_len) {
    (void)bind_ctx; (void)client_ip; (void)buf_size;
    mock_accept_call_count++;
    if (mock_accept_call_count > mock_accept_max_calls) {
        return -1;
    }
    client_ctx->fd = 43;
    if (ip_len) *ip_len = 0;
    return 0;
}
void mbedtls_ssl_set_bio(mbedtls_ssl_context *ssl, void *p_bio,
                          int (*f_send)(void *, const unsigned char *, size_t),
                          int (*f_recv)(void *, unsigned char *, size_t),
                          int (*f_recv_timeout)(void *, unsigned char *, size_t, uint32_t)) {
    (void)ssl; (void)p_bio; (void)f_send; (void)f_recv; (void)f_recv_timeout;
}
int mbedtls_ssl_handshake(mbedtls_ssl_context *ssl) {
    if (mock_psk_cb_capture && captured_psk_cb) {
        const unsigned char *id = (const unsigned char *)"robot-client";
        captured_psk_cb(captured_psk_cb_param, ssl, id, 12);
        mock_psk_cb_called = 1;
    }
    return mock_handshake_result;
}
int mbedtls_ssl_read(mbedtls_ssl_context *ssl, unsigned char *buf, size_t len) {
    (void)ssl;
    if (mock_read_data && mock_read_data_offset < mock_read_data_len) {
        size_t remaining = mock_read_data_len - mock_read_data_offset;
        size_t to_copy = remaining < len ? remaining : len;
        memcpy(buf, mock_read_data + mock_read_data_offset, to_copy);
        mock_read_data_offset += to_copy;
        return (int)to_copy;
    }
    return mock_read_result;
}
int mbedtls_ssl_write(mbedtls_ssl_context *ssl, const unsigned char *buf, size_t len) {
    (void)ssl; (void)buf;
    return (int)len;
}
int mbedtls_ssl_session_reset(mbedtls_ssl_context *ssl) { (void)ssl; return 0; }
void mbedtls_ssl_session_init(mbedtls_ssl_session *session) { memset(session, 0, sizeof(*session)); }
void mbedtls_ssl_session_free(mbedtls_ssl_session *session) { (void)session; }
int mbedtls_ssl_close_notify(mbedtls_ssl_context *ssl) { (void)ssl; return 0; }
const char *mbedtls_ssl_get_ciphersuite(const mbedtls_ssl_context *ssl) {
    (void)ssl; return "TLS-PSK-WITH-AES-128-GCM-SHA256";
}
int mbedtls_ssl_set_hs_psk(mbedtls_ssl_context *ssl, const unsigned char *psk, size_t psk_len) {
    (void)ssl; (void)psk; (void)psk_len; return 0;
}

int mbedtls_net_send(void *ctx, const unsigned char *buf, size_t len) {
    (void)ctx; (void)buf; return (int)len;
}
int mbedtls_net_recv(void *ctx, unsigned char *buf, size_t len) {
    (void)ctx; (void)buf; (void)len; return MBEDTLS_ERR_SSL_WANT_READ;
}
int mbedtls_net_recv_timeout(void *ctx, unsigned char *buf, size_t len, uint32_t timeout) {
    (void)ctx; (void)buf; (void)len; (void)timeout; return MBEDTLS_ERR_SSL_WANT_READ;
}

// Session cache stubs
void mbedtls_ssl_cache_init(mbedtls_ssl_cache_context *cache) { (void)cache; }
void mbedtls_ssl_cache_free(mbedtls_ssl_cache_context *cache) { (void)cache; }
void mbedtls_ssl_cache_set_timeout(mbedtls_ssl_cache_context *cache, int timeout) { (void)cache; (void)timeout; }
void mbedtls_ssl_cache_set_max_entries(mbedtls_ssl_cache_context *cache, int max) { (void)cache; (void)max; }
int mbedtls_ssl_cache_get(void *data, mbedtls_ssl_session *session) { (void)data; (void)session; return -1; }
int mbedtls_ssl_cache_set(void *data, const mbedtls_ssl_session *session) { (void)data; (void)session; return 0; }
void mbedtls_ssl_conf_session_cache(mbedtls_ssl_config *conf, void *p_cache,
                                     int (*f_get)(void *, mbedtls_ssl_session *),
                                     int (*f_set)(void *, const mbedtls_ssl_session *)) {
    (void)conf; (void)p_cache; (void)f_get; (void)f_set;
}
int mbedtls_ssl_get_session(const mbedtls_ssl_context *ssl, mbedtls_ssl_session *session) {
    (void)ssl; (void)session; return 0;
}
