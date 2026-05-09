# Fleet Telemetry

This document describes the fleet monitoring architecture for production deployments of the 3WE Robot Platform.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────┐
│  Robot #1   │     │  Robot #2   │     │  MQTT Broker    │     │ Grafana  │
│             │     │             │     │  (Mosquitto)    │     │          │
│ diagnostics ├────►│ diagnostics ├────►│                 ├────►│ Dashboard│
│ mqtt_bridge │MQTT │ mqtt_bridge │MQTT │ fleet/+/diag    │     │          │
└─────────────┘     └─────────────┘     └────────┬────────┘     └──────────┘
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │ Telegraf/InfluxDB│
                                         │ (Time Series DB) │
                                         └─────────────────┘
```

## Components

### 1. Diagnostics Node (`robot_diagnostics`)

Runs on each robot's companion computer. Subscribes to platform health topics and publishes a unified `DiagnosticArray` at 1 Hz.

```bash
ros2 run robot_diagnostics diagnostics_node --ros-args \
  -p robot_id:=robot-001 \
  -p publish_rate_hz:=1.0
```

### 2. MQTT Bridge Node (`mqtt_bridge_node`)

Forwards `/diagnostics` messages to a fleet MQTT broker.

```bash
ros2 run robot_diagnostics mqtt_bridge_node --ros-args \
  -p broker_url:=mqtt://fleet-broker.local:1883 \
  -p username:=robot \
  -p password:=secret \
  -p robot_id:=robot-001 \
  -p topic_prefix:=fleet/ \
  -p qos:=1
```

### 3. MQTT Broker (Mosquitto)

Central broker collecting telemetry from all robots.

```yaml
# mosquitto.conf
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
persistence true
persistence_location /var/lib/mosquitto/
```

### 4. InfluxDB + Telegraf

Telegraf subscribes to MQTT topics and writes to InfluxDB.

```toml
# telegraf.conf
[[inputs.mqtt_consumer]]
  servers = ["tcp://localhost:1883"]
  topics = ["fleet/+/diagnostics"]
  data_format = "json"
  json_time_key = "timestamp"
  json_time_format = "unix"
  tag_keys = ["robot_id"]

[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "$INFLUX_TOKEN"
  organization = "robot-platform"
  bucket = "fleet_telemetry"
```

## MQTT Topic Schema

```
fleet/{robot_id}/diagnostics
```

Payload (JSON):
```json
{
  "timestamp": 1705312200.123,
  "robot_id": "robot-001",
  "status": [
    {
      "name": "robot-001/system",
      "level": 0,
      "message": "Running",
      "values": {
        "uptime_s": "3621.5",
        "robot_id": "robot-001"
      }
    },
    {
      "name": "robot-001/battery",
      "level": 0,
      "message": "OK: 78%",
      "values": {
        "percentage": "78.2",
        "voltage_v": "7.84"
      }
    },
    {
      "name": "robot-001/safety",
      "level": 0,
      "message": "Normal operation",
      "values": {
        "estop_active": "false"
      }
    }
  ]
}
```

## Diagnostic Levels

| Level | Name | Meaning |
|-------|------|---------|
| 0 | OK | Operating normally |
| 1 | WARN | Degraded (e.g., low battery, E-stop active) |
| 2 | ERROR | Critical issue (e.g., battery <10%) |
| 3 | STALE | No data received (sensor offline) |

## Alerting Rules

Configure in Grafana or Alertmanager:

| Condition | Severity | Action |
|-----------|----------|--------|
| Battery < 10% | Critical | Notify ops, initiate safe shutdown |
| E-stop active > 5 min | Warning | Investigate stuck robot |
| Topic rate = 0 for > 30s | Warning | Communication failure |
| Uptime reset unexpected | Info | Robot rebooted (check core dump) |
| No telemetry > 2 min | Critical | Robot offline |

## Quick Start (Docker Compose)

The `docker-compose.yml` in the project root includes an optional MQTT broker:

```bash
docker compose --profile fleet up -d
```

This starts:
- Mosquitto MQTT broker on port 1883
- The robot companion stack (rosbridge + diagnostics + web UI)

For a full monitoring stack, add Telegraf + InfluxDB + Grafana to your fleet infrastructure.

## Data Retention

Recommended retention policy:
- Raw telemetry (1 Hz): 7 days
- Aggregated (1 min): 90 days
- Aggregated (1 hour): 2 years

Configure in InfluxDB bucket retention rules.

## Security

- MQTT connections should use TLS (`mqtts://`) in production
- Each robot gets unique MQTT credentials (username = robot_id)
- Broker ACLs restrict each robot to its own topic subtree
- Fleet dashboard access requires separate authentication
