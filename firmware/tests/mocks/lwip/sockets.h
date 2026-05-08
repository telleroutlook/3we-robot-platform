// SPDX-License-Identifier: Apache-2.0
#ifndef MOCK_LWIP_SOCKETS_H
#define MOCK_LWIP_SOCKETS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <sys/types.h>

#ifdef __APPLE__
#include <arpa/inet.h>
#include <sys/time.h>
#include <sys/socket.h>
#else
#include <arpa/inet.h>
#include <sys/time.h>
#include <sys/socket.h>
#endif

#ifndef AF_INET
#define AF_INET         2
#endif
#ifndef SOCK_DGRAM
#define SOCK_DGRAM      2
#endif
#ifndef IPPROTO_UDP
#define IPPROTO_UDP     17
#endif
#ifndef SOL_SOCKET
#define SOL_SOCKET      0xfff
#endif
#ifndef SO_RCVTIMEO
#define SO_RCVTIMEO     0x1006
#endif
#ifndef INADDR_ANY
#define INADDR_ANY      0
#endif
#ifndef INET_ADDRSTRLEN
#define INET_ADDRSTRLEN 16
#endif

int mock_socket(int domain, int type, int protocol);
int mock_bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
int mock_sendto(int sockfd, const void *buf, size_t len, int flags,
                const struct sockaddr *dest_addr, socklen_t addrlen);
int mock_recvfrom(int sockfd, void *buf, size_t len, int flags,
                  struct sockaddr *src_addr, socklen_t *addrlen);
int mock_setsockopt(int sockfd, int level, int optname,
                    const void *optval, socklen_t optlen);
int mock_close(int fd);

#define socket  mock_socket
#define bind    mock_bind
#define sendto  mock_sendto
#define recvfrom mock_recvfrom
#define setsockopt mock_setsockopt
#define close   mock_close

static inline char *inet_ntoa_r(struct in_addr addr, char *buf, int buflen) {
    (void)addr; (void)buflen;
    buf[0] = '1'; buf[1] = '.'; buf[2] = '2'; buf[3] = '.';
    buf[4] = '3'; buf[5] = '.'; buf[6] = '4'; buf[7] = '\0';
    return buf;
}

void mock_lwip_reset(void);
void mock_lwip_set_socket_fail(bool fail);
void mock_lwip_set_bind_fail(bool fail);
void mock_lwip_set_sendto_result(int result);
void mock_lwip_set_recvfrom_data(const uint8_t *data, size_t len,
                                  uint32_t src_ip, uint16_t src_port);

#endif // MOCK_LWIP_SOCKETS_H
