# Monitoring Stack

Prometheus + Grafana observability for the robot fleet.

## Quick Start

```bash
cd monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (default: admin/admin)

## Architecture

```
[Robot ROS2 Stack] → metrics_exporter.py → :9101/metrics
                                                  ↓
                                        [Prometheus :9090]
                                                  ↓
                                        [Grafana :3000]
```

## Metrics Exporter

The `metrics_exporter.py` is a ROS2 node that subscribes to robot topics and
exposes them as Prometheus-compatible metrics. Run it on the companion computer:

```bash
# As a ROS2 node
ros2 run robot_diagnostics metrics_exporter

# Or standalone (requires rclpy)
python3 monitoring/metrics_exporter.py
```

### Exported Metrics

| Metric | Source Topic | Unit |
|--------|-------------|------|
| `robot_battery_voltage` | /robot/battery | V |
| `robot_battery_current_amps` | /robot/battery | A |
| `robot_battery_percentage` | /robot/battery | 0-1 |
| `robot_cmd_vel_linear_x` | /robot/cmd_vel | m/s |
| `robot_cmd_vel_angular_z` | /robot/cmd_vel | rad/s |
| `robot_emergency_stop_active` | /robot/emergency_stop | 0/1 |
| `robot_imu_linear_accel_{x,y,z}` | /robot/imu | m/s² |
| `robot_range_front_meters` | /robot/range/front | m |

## Grafana Dashboard

The pre-built dashboard (`grafana/robot-overview-dashboard.json`) includes:

- Battery voltage and percentage over time
- Emergency stop status indicator
- Velocity command traces
- IMU acceleration graphs
- Front range sensor gauge
- Current draw monitoring

Import manually or use the provisioning volume mount.

## Fleet Monitoring

For multi-robot setups, add targets to `prometheus.yml`:

```yaml
- targets: ['robot-001:9101', 'robot-002:9101', 'robot-003:9101']
```

Use the `robot_id` template variable in Grafana to filter by robot.
