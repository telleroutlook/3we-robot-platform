// SPDX-License-Identifier: Apache-2.0
// Mock mbedtls SSL/networking functions for DTLS transport unit testing
#ifndef MBEDTLS_SSL_STUBS_H
#define MBEDTLS_SSL_STUBS_H

#include <stdint.h>
#include <stddef.h>

// --- mbedtls SSL types ---
typedef struct { int dummy; } mbedtls_ssl_context;
typedef struct { int dummy; } mbedtls_ssl_config;
typedef struct { int fd; } mbedtls_net_context;
typedef struct { int dummy; } mbedtls_entropy_context;
typedef struct { int dummy; } mbedtls_ctr_drbg_context;
typedef struct { int dummy; } mbedtls_ssl_cookie_ctx;
typedef struct { uint32_t fin_ms; uint32_t int_ms; } mbedtls_timing_delay_context;

// --- SSL transport/preset constants ---
#define MBEDTLS_SSL_IS_SERVER          1
#define MBEDTLS_SSL_TRANSPORT_DATAGRAM 1
#define MBEDTLS_SSL_PRESET_DEFAULT     0
#define MBEDTLS_SSL_VERSION_TLS1_2     0x0303
#define MBEDTLS_NET_PROTO_UDP          1

// Ciphersuite IDs
#define MBEDTLS_TLS_PSK_WITH_AES_128_GCM_SHA256 0x00A8
#define MBEDTLS_TLS_PSK_WITH_AES_256_GCM_SHA384 0x00A9
#define MBEDTLS_TLS_PSK_WITH_AES_128_CCM        0xC0A4

// Error codes
#define MBEDTLS_ERR_SSL_WANT_READ       (-0x6900)
#define MBEDTLS_ERR_SSL_WANT_WRITE      (-0x6880)
#define MBEDTLS_ERR_SSL_TIMEOUT         (-0x6800)
#define MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY (-0x7880)

// --- Function declarations (all no-op for host testing) ---
void mbedtls_ssl_init(mbedtls_ssl_context *ssl);
void mbedtls_ssl_config_init(mbedtls_ssl_config *conf);
void mbedtls_entropy_init(mbedtls_entropy_context *ctx);
void mbedtls_ctr_drbg_init(mbedtls_ctr_drbg_context *ctx);
void mbedtls_ssl_cookie_init(mbedtls_ssl_cookie_ctx *ctx);
void mbedtls_net_init(mbedtls_net_context *ctx);

void mbedtls_ssl_free(mbedtls_ssl_context *ssl);
void mbedtls_ssl_config_free(mbedtls_ssl_config *conf);
void mbedtls_entropy_free(mbedtls_entropy_context *ctx);
void mbedtls_ctr_drbg_free(mbedtls_ctr_drbg_context *ctx);
void mbedtls_ssl_cookie_free(mbedtls_ssl_cookie_ctx *ctx);
void mbedtls_net_free(mbedtls_net_context *ctx);

typedef int (*mbedtls_entropy_f_source_ptr)(void *, unsigned char *, size_t, size_t *);
int mbedtls_entropy_func(void *data, unsigned char *output, size_t len);
int mbedtls_ctr_drbg_random(void *p_rng, unsigned char *output, size_t output_len);
int mbedtls_ctr_drbg_seed(mbedtls_ctr_drbg_context *ctx,
                            int (*f_entropy)(void *, unsigned char *, size_t),
                            void *p_entropy, const unsigned char *custom, size_t len);

int mbedtls_ssl_config_defaults(mbedtls_ssl_config *conf, int endpoint, int transport, int preset);
void mbedtls_ssl_conf_min_tls_version(mbedtls_ssl_config *conf, int ver);
void mbedtls_ssl_conf_rng(mbedtls_ssl_config *conf,
                           int (*f_rng)(void *, unsigned char *, size_t), void *p_rng);
void mbedtls_ssl_conf_psk_cb(mbedtls_ssl_config *conf,
                              int (*f_psk)(void *, mbedtls_ssl_context *, const unsigned char *, size_t),
                              void *p_psk);
int mbedtls_ssl_cookie_setup(mbedtls_ssl_cookie_ctx *ctx,
                              int (*f_rng)(void *, unsigned char *, size_t), void *p_rng);
int mbedtls_ssl_cookie_write(void *ctx, unsigned char **p, unsigned char *end,
                              const unsigned char *info, size_t ilen);
int mbedtls_ssl_cookie_check(void *ctx, const unsigned char *cookie, size_t clen,
                              const unsigned char *info, size_t ilen);
void mbedtls_ssl_conf_dtls_cookies(mbedtls_ssl_config *conf,
                                    int (*f_cookie_write)(void *, unsigned char **, unsigned char *, const unsigned char *, size_t),
                                    int (*f_cookie_check)(void *, const unsigned char *, size_t, const unsigned char *, size_t),
                                    void *p_cookie);
void mbedtls_ssl_conf_handshake_timeout(mbedtls_ssl_config *conf, uint32_t min, uint32_t max);
void mbedtls_ssl_conf_read_timeout(mbedtls_ssl_config *conf, uint32_t timeout);
void mbedtls_ssl_conf_ciphersuites(mbedtls_ssl_config *conf, const int *ciphersuites);
int mbedtls_ssl_setup(mbedtls_ssl_context *ssl, const mbedtls_ssl_config *conf);
void mbedtls_ssl_set_timer_cb(mbedtls_ssl_context *ssl, void *p_timer,
                               void (*f_set_timer)(void *, uint32_t, uint32_t),
                               int (*f_get_timer)(void *));
void mbedtls_timing_set_delay(void *data, uint32_t int_ms, uint32_t fin_ms);
int mbedtls_timing_get_delay(void *data);

int mbedtls_net_bind(mbedtls_net_context *ctx, const char *bind_ip, const char *port, int proto);
int mbedtls_net_accept(mbedtls_net_context *bind_ctx, mbedtls_net_context *client_ctx,
                        void *client_ip, size_t buf_size, size_t *ip_len);
void mbedtls_ssl_set_bio(mbedtls_ssl_context *ssl, void *p_bio,
                          int (*f_send)(void *, const unsigned char *, size_t),
                          int (*f_recv)(void *, unsigned char *, size_t),
                          int (*f_recv_timeout)(void *, unsigned char *, size_t, uint32_t));
int mbedtls_ssl_handshake(mbedtls_ssl_context *ssl);
int mbedtls_ssl_read(mbedtls_ssl_context *ssl, unsigned char *buf, size_t len);
int mbedtls_ssl_write(mbedtls_ssl_context *ssl, const unsigned char *buf, size_t len);
int mbedtls_ssl_session_reset(mbedtls_ssl_context *ssl);
int mbedtls_ssl_close_notify(mbedtls_ssl_context *ssl);
const char *mbedtls_ssl_get_ciphersuite(const mbedtls_ssl_context *ssl);
int mbedtls_ssl_set_hs_psk(mbedtls_ssl_context *ssl, const unsigned char *psk, size_t psk_len);

int mbedtls_net_send(void *ctx, const unsigned char *buf, size_t len);
int mbedtls_net_recv(void *ctx, unsigned char *buf, size_t len);
int mbedtls_net_recv_timeout(void *ctx, unsigned char *buf, size_t len, uint32_t timeout);

#endif // MBEDTLS_SSL_STUBS_H
