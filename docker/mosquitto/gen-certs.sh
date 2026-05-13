#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Generate a self-signed CA and server TLS certificate for the MQTT broker.
# Run once before first docker compose up --profile fleet.
# For production, replace with certificates from a trusted CA.
#
# Usage: ./docker/mosquitto/gen-certs.sh

set -e

CERTS_DIR="$(dirname "$0")/certs"
mkdir -p "$CERTS_DIR"

# CA key and certificate
openssl genrsa -out "$CERTS_DIR/ca.key" 4096
openssl req -new -x509 -days 3650 -key "$CERTS_DIR/ca.key" \
    -out "$CERTS_DIR/ca.crt" \
    -subj "/CN=Robot Platform MQTT CA"

# Server key and CSR
openssl genrsa -out "$CERTS_DIR/server.key" 4096
openssl req -new -key "$CERTS_DIR/server.key" \
    -out "$CERTS_DIR/server.csr" \
    -subj "/CN=mqtt-broker"

# Sign server certificate with CA
openssl x509 -req -days 3650 \
    -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" \
    -CAkey "$CERTS_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERTS_DIR/server.crt"

rm "$CERTS_DIR/server.csr" "$CERTS_DIR/ca.srl" 2>/dev/null || true
chmod 600 "$CERTS_DIR/server.key" "$CERTS_DIR/ca.key"

echo "TLS certificates written to $CERTS_DIR"
echo "Distribute ca.crt to MQTT clients for server verification."
