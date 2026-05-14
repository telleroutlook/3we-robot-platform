# SPDX-License-Identifier: Apache-2.0
"""
ROS2 Prometheus Metrics Exporter Node.

Subscribes to key robot topics and exposes metrics at :9101/metrics
for Prometheus scraping. Designed to run on the companion computer.
"""

import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, Imu, Range
from std_msgs.msg import Bool, Float32


class MetricsStore:
    """Thread-safe metrics storage."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: dict[str, float] = {}
        self._labels: dict[str, dict[str, str]] = {}

    def set(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            self._metrics[name] = value
            if labels:
                self._labels[name] = labels

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, value in sorted(self._metrics.items()):
                labels = self._labels.get(name, {})
                if labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                    lines.append(f"{name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"


store = MetricsStore()


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/metrics":
            body = store.render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            body = b'{"status":"ok"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class MetricsExporter(Node):
    def __init__(self) -> None:
        super().__init__("metrics_exporter")

        self.declare_parameter("port", 9101)
        self.declare_parameter("bind_address", "0.0.0.0")
        port = self.get_parameter("port").get_parameter_value().integer_value
        bind_addr = (
            self.get_parameter("bind_address").get_parameter_value().string_value
        )

        self.create_subscription(BatteryState, "/battery_state", self._on_battery, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(Bool, "/emergency_stop", self._on_estop, 10)
        self.create_subscription(Imu, "/imu/data", self._on_imu, 10)
        self.create_subscription(Range, "/ultrasonic/front", self._on_range_front, 10)
        self.create_subscription(Float32, "/motor/current", self._on_motor_current, 10)

        self._system_timer = self.create_timer(5.0, self._collect_system_metrics)

        self._http_server = HTTPServer((bind_addr, port), MetricsHTTPHandler)
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever, daemon=True
        )
        self._http_thread.start()

        self.get_logger().info(f"Metrics exporter serving on :{port}/metrics")

    def _on_battery(self, msg: BatteryState) -> None:
        store.set("robot_battery_voltage", msg.voltage)
        store.set("robot_battery_current_amps", msg.current)
        pct = msg.percentage * 100.0 if msg.percentage <= 1.0 else msg.percentage
        store.set("robot_battery_percentage", pct)
        store.set("robot_battery_power_supply_status", float(msg.power_supply_status))

    def _on_cmd_vel(self, msg: Twist) -> None:
        store.set("robot_cmd_vel_linear_x", msg.linear.x)
        store.set("robot_cmd_vel_angular_z", msg.angular.z)

    def _on_estop(self, msg: Bool) -> None:
        store.set("robot_emergency_stop_active", 1.0 if msg.data else 0.0)

    def _on_imu(self, msg: Imu) -> None:
        store.set("robot_imu_linear_accel_x", msg.linear_acceleration.x)
        store.set("robot_imu_linear_accel_y", msg.linear_acceleration.y)
        store.set("robot_imu_linear_accel_z", msg.linear_acceleration.z)

    def _on_range_front(self, msg: Range) -> None:
        store.set("robot_range_front_meters", msg.range)

    def _on_motor_current(self, msg: Float32) -> None:
        store.set("robot_motor_current_amps", msg.data)

    def _collect_system_metrics(self) -> None:
        cpu_temp = self._read_cpu_temperature()
        if cpu_temp is not None:
            store.set("robot_cpu_temp", cpu_temp)

        mem_pct = self._read_memory_percent()
        if mem_pct is not None:
            store.set("robot_memory_percent", mem_pct)

        disk_free = self._read_disk_free_gb()
        if disk_free is not None:
            store.set("robot_disk_free_gb", disk_free)

        rssi = self._read_wifi_rssi()
        if rssi is not None:
            store.set("robot_wifi_rssi", float(rssi))

    def _read_cpu_temperature(self) -> float | None:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000.0
        except (OSError, ValueError):
            return None

    def _read_memory_percent(self) -> float | None:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            info: dict[str, int] = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 0)
            available = info.get("MemAvailable", 0)
            if total <= 0:
                return None
            return (1.0 - available / total) * 100.0
        except (OSError, ValueError, KeyError):
            return None

    def _read_disk_free_gb(self) -> float | None:
        try:
            stat = os.statvfs("/")
            return (stat.f_bavail * stat.f_frsize) / (1024 * 1024 * 1024)
        except OSError:
            return None

    def _read_wifi_rssi(self) -> int | None:
        try:
            result = subprocess.run(
                ["iwconfig", "wlan0"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            for line in result.stdout.split("\n"):
                if "Signal level" in line:
                    for part in line.split():
                        if part.startswith("level="):
                            return int(part.split("=")[1])
            return None
        except (subprocess.TimeoutExpired, OSError, ValueError):
            return None

    def destroy_node(self) -> None:
        self._http_server.shutdown()
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = MetricsExporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
