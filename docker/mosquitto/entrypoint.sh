#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Generate password file from environment if it does not already exist.

PASSWD_FILE=/mosquitto/config/passwd

if [ ! -f "$PASSWD_FILE" ]; then
    MQTT_USER="${MQTT_USER:-robot}"
    if [ -z "$MQTT_PASS" ]; then
        echo "ERROR: MQTT_PASS environment variable must be set" >&2
        exit 1
    fi
    mosquitto_passwd -b -c "$PASSWD_FILE" "$MQTT_USER" "$MQTT_PASS"
    echo "Created MQTT credentials for user: $MQTT_USER"
fi

exec mosquitto -c /mosquitto/config/mosquitto.conf
