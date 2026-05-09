// SPDX-License-Identifier: Apache-2.0
#include "captive_portal.h"
#include "wifi_provision.h"

#include "esp_log.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "lwip/sockets.h"
#include "cJSON.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>
#include <stdio.h>

static const char *TAG = "captive_portal";

static httpd_handle_t s_httpd = NULL;
static TaskHandle_t s_dns_task = NULL;
static bool s_active = false;
static captive_portal_done_cb_t s_done_cb = NULL;

#define DNS_PORT        53
#define AP_IP           "192.168.4.1"
#define DNS_STACK_SIZE  2048

static const char CONFIG_PAGE_HTML[] =
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Robot Platform WiFi Setup</title>"
    "<style>"
    "body{font-family:sans-serif;max-width:400px;margin:40px auto;padding:0 20px;background:#f5f5f5}"
    ".card{background:#fff;border-radius:8px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.1)}"
    "h1{font-size:1.3em;color:#333;margin:0 0 16px}"
    "label{display:block;margin:12px 0 4px;font-size:.9em;color:#555}"
    "input{width:100%;padding:10px;border:1px solid #ddd;border-radius:4px;box-sizing:border-box}"
    "button{width:100%;padding:12px;margin-top:20px;background:#1976d2;color:#fff;"
    "border:none;border-radius:4px;font-size:1em;cursor:pointer}"
    "button:hover{background:#1565c0}"
    "#status{margin-top:12px;font-size:.85em;color:#666}"
    "</style></head><body>"
    "<div class='card'><h1>Robot Platform WiFi</h1>"
    "<form id='f'>"
    "<label for='s'>Network Name (SSID)</label>"
    "<input id='s' name='ssid' required maxlength='32'>"
    "<label for='p'>Password</label>"
    "<input id='p' name='password' type='password' maxlength='63'>"
    "<button type='submit'>Connect</button>"
    "</form><div id='status'></div></div>"
    "<script>"
    "document.getElementById('f').onsubmit=async function(e){"
    "e.preventDefault();const st=document.getElementById('status');"
    "st.textContent='Connecting...';"
    "const r=await fetch('/connect',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({ssid:document.getElementById('s').value,"
    "password:document.getElementById('p').value})});"
    "const j=await r.json();st.textContent=j.message;}"
    "</script></body></html>";

static void dns_server_task(void *arg)
{
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        ESP_LOGE(TAG, "DNS socket creation failed");
        vTaskDelete(NULL);
        return;
    }

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(DNS_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        ESP_LOGE(TAG, "DNS socket bind failed");
        close(sock);
        vTaskDelete(NULL);
        return;
    }

    struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    uint8_t buf[512];
    struct sockaddr_in client;
    socklen_t client_len = sizeof(client);

    while (s_active) {
        int len = recvfrom(sock, buf, sizeof(buf), 0,
                           (struct sockaddr *)&client, &client_len);
        if (len < 12) continue;

        // Build minimal DNS response: redirect all queries to AP IP
        buf[2] = 0x81; buf[3] = 0x80; // flags: response, no error
        buf[6] = buf[4]; buf[7] = buf[5]; // answer count = question count
        // Append answer section pointing to AP IP
        int resp_len = len;
        if (resp_len + 16 <= (int)sizeof(buf)) {
            buf[resp_len++] = 0xC0; buf[resp_len++] = 0x0C; // name pointer
            buf[resp_len++] = 0x00; buf[resp_len++] = 0x01; // type A
            buf[resp_len++] = 0x00; buf[resp_len++] = 0x01; // class IN
            buf[resp_len++] = 0x00; buf[resp_len++] = 0x00;
            buf[resp_len++] = 0x00; buf[resp_len++] = 0x0A; // TTL 10s
            buf[resp_len++] = 0x00; buf[resp_len++] = 0x04; // data length
            buf[resp_len++] = 192;  buf[resp_len++] = 168;
            buf[resp_len++] = 4;    buf[resp_len++] = 1;    // 192.168.4.1
        }
        sendto(sock, buf, resp_len, 0,
               (struct sockaddr *)&client, client_len);
    }

    close(sock);
    vTaskDelete(NULL);
}

static esp_err_t handler_get_root(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, CONFIG_PAGE_HTML, sizeof(CONFIG_PAGE_HTML) - 1);
}

static esp_err_t handler_captive_detect(httpd_req_t *req)
{
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");
    return httpd_resp_send(req, NULL, 0);
}

static esp_err_t handler_post_connect(httpd_req_t *req)
{
    char body[256] = {0};
    int received = httpd_req_recv(req, body, sizeof(body) - 1);
    if (received <= 0) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Empty body");
        return ESP_FAIL;
    }

    cJSON *json = cJSON_Parse(body);
    if (!json) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid JSON");
        return ESP_FAIL;
    }

    const cJSON *ssid_item = cJSON_GetObjectItem(json, "ssid");
    const cJSON *pass_item = cJSON_GetObjectItem(json, "password");

    if (!cJSON_IsString(ssid_item) || strlen(ssid_item->valuestring) == 0) {
        cJSON_Delete(json);
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Missing SSID");
        return ESP_FAIL;
    }

    const char *ssid = ssid_item->valuestring;
    const char *password = cJSON_IsString(pass_item) ? pass_item->valuestring : "";

    esp_err_t ret = wifi_provision_store_credentials(ssid, password);
    cJSON_Delete(json);

    if (ret != ESP_OK) {
        httpd_resp_set_type(req, "application/json");
        httpd_resp_send(req, "{\"success\":false,\"message\":\"Failed to store credentials\"}", -1);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, "{\"success\":true,\"message\":\"Credentials saved. Rebooting to connect...\"}", -1);

    if (s_done_cb) {
        s_done_cb(ssid, password);
    }

    return ESP_OK;
}

static esp_err_t handler_get_status(httpd_req_t *req)
{
    wifi_ap_record_t ap_info;
    bool connected = (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK);

    char resp[128];
    snprintf(resp, sizeof(resp),
             "{\"connected\":%s,\"ap_mode\":%s}",
             connected ? "true" : "false",
             s_active ? "true" : "false");
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, resp, -1);
}

esp_err_t captive_portal_start(const captive_portal_config_t *config)
{
    if (s_active) return ESP_ERR_INVALID_STATE;

    s_done_cb = config ? config->on_credentials_received : NULL;
    uint8_t channel = (config && config->wifi_channel) ? config->wifi_channel : 6;

    // Initialize network interface if not done
    ESP_ERROR_CHECK(esp_netif_init());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t wifi_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&wifi_cfg));

    // Derive AP SSID from MAC
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    char ap_ssid[32];
    snprintf(ap_ssid, sizeof(ap_ssid), "RobotPlatform_%02X%02X", mac[4], mac[5]);

    wifi_config_t wifi_ap_cfg = {
        .ap = {
            .channel = channel,
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    strncpy((char *)wifi_ap_cfg.ap.ssid, ap_ssid, sizeof(wifi_ap_cfg.ap.ssid));
    wifi_ap_cfg.ap.ssid_len = (uint8_t)strlen(ap_ssid);

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_ap_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "AP started: %s (channel %d)", ap_ssid, channel);

    // Start HTTP server
    httpd_config_t httpd_cfg = HTTPD_DEFAULT_CONFIG();
    httpd_cfg.max_uri_handlers = 8;
    httpd_cfg.lru_purge_enable = true;

    esp_err_t ret = httpd_start(&s_httpd, &httpd_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "HTTP server start failed: %s", esp_err_to_name(ret));
        return ret;
    }

    const httpd_uri_t uri_root = { .uri = "/", .method = HTTP_GET, .handler = handler_get_root };
    const httpd_uri_t uri_204 = { .uri = "/generate_204", .method = HTTP_GET, .handler = handler_captive_detect };
    const httpd_uri_t uri_hotspot = { .uri = "/hotspot-detect.html", .method = HTTP_GET, .handler = handler_captive_detect };
    const httpd_uri_t uri_connect = { .uri = "/connect", .method = HTTP_POST, .handler = handler_post_connect };
    const httpd_uri_t uri_status = { .uri = "/status", .method = HTTP_GET, .handler = handler_get_status };

    httpd_register_uri_handler(s_httpd, &uri_root);
    httpd_register_uri_handler(s_httpd, &uri_204);
    httpd_register_uri_handler(s_httpd, &uri_hotspot);
    httpd_register_uri_handler(s_httpd, &uri_connect);
    httpd_register_uri_handler(s_httpd, &uri_status);

    // Start DNS redirect task
    s_active = true;
    BaseType_t rc = xTaskCreate(dns_server_task, "dns_redir", DNS_STACK_SIZE, NULL, 2, &s_dns_task);
    if (rc != pdPASS) {
        ESP_LOGW(TAG, "DNS task creation failed - captive detection may not work");
    }

    ESP_LOGI(TAG, "Captive portal active at http://192.168.4.1/");
    return ESP_OK;
}

esp_err_t captive_portal_stop(void)
{
    if (!s_active) return ESP_OK;

    s_active = false;

    if (s_dns_task) {
        vTaskDelay(pdMS_TO_TICKS(1100));
        s_dns_task = NULL;
    }

    if (s_httpd) {
        httpd_stop(s_httpd);
        s_httpd = NULL;
    }

    esp_wifi_stop();

    ESP_LOGI(TAG, "Captive portal stopped");
    return ESP_OK;
}

bool captive_portal_is_active(void)
{
    return s_active;
}

httpd_handle_t captive_portal_get_httpd(void)
{
    return s_httpd;
}
