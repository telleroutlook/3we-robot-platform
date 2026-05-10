// SPDX-License-Identifier: Apache-2.0
#include "lwip/sockets.h"
#include <string.h>

static bool socket_fail = false;
static bool bind_fail = false;
static int sendto_result = 10;
static int next_fd = 3;

static const uint8_t *recv_data = NULL;
static size_t recv_len = 0;
static uint32_t recv_src_ip = 0;
static uint16_t recv_src_port = 0;

void mock_lwip_reset(void)
{
    socket_fail = false;
    bind_fail = false;
    sendto_result = 10;
    next_fd = 3;
    recv_data = NULL;
    recv_len = 0;
    recv_src_ip = 0;
    recv_src_port = 0;
}

void mock_lwip_set_socket_fail(bool fail)
{
    socket_fail = fail;
}

void mock_lwip_set_bind_fail(bool fail)
{
    bind_fail = fail;
}

void mock_lwip_set_sendto_result(int result)
{
    sendto_result = result;
}

void mock_lwip_set_recvfrom_data(const uint8_t *data, size_t len,
                                  uint32_t src_ip, uint16_t src_port)
{
    recv_data = data;
    recv_len = len;
    recv_src_ip = src_ip;
    recv_src_port = src_port;
}

int mock_socket(int domain, int type, int protocol)
{
    (void)domain; (void)type; (void)protocol;
    if (socket_fail) return -1;
    return next_fd++;
}

int mock_bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen)
{
    (void)sockfd; (void)addr; (void)addrlen;
    if (bind_fail) return -1;
    return 0;
}

int mock_sendto(int sockfd, const void *buf, size_t len, int flags,
                const struct sockaddr *dest_addr, socklen_t addrlen)
{
    (void)sockfd; (void)buf; (void)flags; (void)dest_addr; (void)addrlen;
    if (sendto_result < 0) return -1;
    return (int)len;
}

int mock_recvfrom(int sockfd, void *buf, size_t len, int flags,
                  struct sockaddr *src_addr, socklen_t *addrlen)
{
    (void)sockfd; (void)flags;
    if (!recv_data || recv_len == 0) return -1;

    size_t copy = recv_len < len ? recv_len : len;
    memcpy(buf, recv_data, copy);

    if (src_addr && addrlen) {
        struct sockaddr_in *sin = (struct sockaddr_in *)src_addr;
        sin->sin_family = AF_INET;
        sin->sin_port = htons(recv_src_port);
        sin->sin_addr.s_addr = recv_src_ip;
        *addrlen = sizeof(struct sockaddr_in);
    }

    recv_data = NULL;
    recv_len = 0;
    return (int)copy;
}

int mock_setsockopt(int sockfd, int level, int optname,
                    const void *optval, socklen_t optlen)
{
    (void)sockfd; (void)level; (void)optname; (void)optval; (void)optlen;
    return 0;
}

int mock_close(int fd)
{
    (void)fd;
    return 0;
}

int mock_select(int nfds, fd_set *readfds, fd_set *writefds,
                fd_set *exceptfds, struct timeval *timeout)
{
    (void)writefds; (void)exceptfds; (void)timeout;
    (void)nfds;
    if (!readfds) return 0;
    return 1;
}
