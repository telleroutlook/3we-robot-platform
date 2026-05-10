# SPDX-License-Identifier: Apache-2.0
"""
System health monitor node for the 3WE Robot Platform.

Monitors CPU temperature, memory usage, WiFi signal, and disk space on the
Pi 5 companion computer. Publishes a composite health score (0-100) and
individual metric statuses for the diagnostics pipeline.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import Float32


@dataclass(frozen=True)
class HealthThresholds:
    cpu_temp_warn: float
    cpu_temp_critical: float
    memory_warn_pct: float
    memory_critical_pct: float
    wifi_rssi_warn: int
    wifi_rssi_critical: int
    disk_warn_gb: float
    disk_critical_gb: float


class HealthMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__("health_monitor")

        self.declare_parameter("publish_rate_hz", 0.5)
        self.declare_parameter("cpu_temp_warn", 75.0)
        self.declare_parameter("cpu_temp_critical", 85.0)
        self.declare_parameter("memory_warn_pct", 85.0)
        self.declare_parameter("memory_critical_pct", 95.0)
        self.declare_parameter("wifi_rssi_warn", -75)
        self.declare_parameter("wifi_rssi_critical", -85)
        self.declare_parameter("disk_warn_gb", 2.0)
        self.declare_parameter("disk_critical_gb", 0.5)

        self._thresholds = HealthThresholds(
            cpu_temp_warn=self.get_parameter("cpu_temp_warn").value,
            cpu_temp_critical=self.get_parameter("cpu_temp_critical").value,
            memory_warn_pct=self.get_parameter("memory_warn_pct").value,
            memory_critical_pct=self.get_parameter("memory_critical_pct").value,
            wifi_rssi_warn=self.get_parameter("wifi_rssi_warn").value,
            wifi_rssi_critical=self.get_parameter("wifi_rssi_critical").value,
            disk_warn_gb=self.get_parameter("disk_warn_gb").value,
            disk_critical_gb=self.get_parameter("disk_critical_gb").value,
        )

        rate = self.get_parameter("publish_rate_hz").value
        if rate <= 0.0:
            rate = 0.5

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self._score_pub = self.create_publisher(Float32, "/robot/health_score", qos)
        self._diag_pub = self.create_publisher(
            DiagnosticArray, "/robot/health_diagnostics", qos
        )

        self._timer = self.create_timer(1.0 / rate, self._check_health)
        self.get_logger().info(
            f"Health monitor started (rate={rate}Hz, "
            f"temp_warn={self._thresholds.cpu_temp_warn}°C)"
        )

    def _check_health(self) -> None:
        cpu_temp = self._read_cpu_temperature()
        mem_pct = self._read_memory_usage()
        rssi = self._read_wifi_rssi()
        disk_gb = self._read_disk_free()

        statuses: list[DiagnosticStatus] = []
        penalties: list[float] = []

        statuses.append(self._evaluate_cpu_temp(cpu_temp, penalties))
        statuses.append(self._evaluate_memory(mem_pct, penalties))
        statuses.append(self._evaluate_wifi(rssi, penalties))
        statuses.append(self._evaluate_disk(disk_gb, penalties))

        score = max(0.0, 100.0 - sum(penalties))

        score_msg = Float32()
        score_msg.data = float(score)
        self._score_pub.publish(score_msg)

        diag_msg = DiagnosticArray()
        diag_msg.header.stamp = self.get_clock().now().to_msg()
        diag_msg.status = statuses
        self._diag_pub.publish(diag_msg)

    def _evaluate_cpu_temp(
        self, temp: Optional[float], penalties: list[float]
    ) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = "CPU Temperature"
        status.hardware_id = "pi5_cpu"

        if temp is None:
            status.level = DiagnosticStatus.STALE
            status.message = "Unable to read temperature"
            return status

        status.values = [KeyValue(key="temperature_c", value=f"{temp:.1f}")]

        if temp >= self._thresholds.cpu_temp_critical:
            status.level = DiagnosticStatus.ERROR
            status.message = f"CRITICAL: {temp:.1f}°C"
            penalties.append(50.0)
        elif temp >= self._thresholds.cpu_temp_warn:
            status.level = DiagnosticStatus.WARN
            status.message = f"Warning: {temp:.1f}°C"
            penalties.append(20.0)
        else:
            status.level = DiagnosticStatus.OK
            status.message = f"Normal: {temp:.1f}°C"

        return status

    def _evaluate_memory(
        self, mem_pct: Optional[float], penalties: list[float]
    ) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = "Memory Usage"
        status.hardware_id = "pi5_ram"

        if mem_pct is None:
            status.level = DiagnosticStatus.STALE
            status.message = "Unable to read memory"
            return status

        status.values = [KeyValue(key="usage_pct", value=f"{mem_pct:.1f}")]

        if mem_pct >= self._thresholds.memory_critical_pct:
            status.level = DiagnosticStatus.ERROR
            status.message = f"CRITICAL: {mem_pct:.1f}%"
            penalties.append(40.0)
        elif mem_pct >= self._thresholds.memory_warn_pct:
            status.level = DiagnosticStatus.WARN
            status.message = f"Warning: {mem_pct:.1f}%"
            penalties.append(15.0)
        else:
            status.level = DiagnosticStatus.OK
            status.message = f"Normal: {mem_pct:.1f}%"

        return status

    def _evaluate_wifi(
        self, rssi: Optional[int], penalties: list[float]
    ) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = "WiFi Signal"
        status.hardware_id = "pi5_wifi"

        if rssi is None:
            status.level = DiagnosticStatus.STALE
            status.message = "WiFi disconnected or unavailable"
            penalties.append(30.0)
            return status

        status.values = [KeyValue(key="rssi_dbm", value=str(rssi))]

        if rssi <= self._thresholds.wifi_rssi_critical:
            status.level = DiagnosticStatus.ERROR
            status.message = f"CRITICAL: {rssi} dBm"
            penalties.append(35.0)
        elif rssi <= self._thresholds.wifi_rssi_warn:
            status.level = DiagnosticStatus.WARN
            status.message = f"Warning: {rssi} dBm"
            penalties.append(15.0)
        else:
            status.level = DiagnosticStatus.OK
            status.message = f"Good: {rssi} dBm"

        return status

    def _evaluate_disk(
        self, free_gb: Optional[float], penalties: list[float]
    ) -> DiagnosticStatus:
        status = DiagnosticStatus()
        status.name = "Disk Space"
        status.hardware_id = "pi5_disk"

        if free_gb is None:
            status.level = DiagnosticStatus.STALE
            status.message = "Unable to read disk space"
            return status

        status.values = [KeyValue(key="free_gb", value=f"{free_gb:.2f}")]

        if free_gb <= self._thresholds.disk_critical_gb:
            status.level = DiagnosticStatus.ERROR
            status.message = f"CRITICAL: {free_gb:.2f} GB free"
            penalties.append(30.0)
        elif free_gb <= self._thresholds.disk_warn_gb:
            status.level = DiagnosticStatus.WARN
            status.message = f"Warning: {free_gb:.2f} GB free"
            penalties.append(10.0)
        else:
            status.level = DiagnosticStatus.OK
            status.message = f"OK: {free_gb:.2f} GB free"

        return status

    def _read_cpu_temperature(self) -> Optional[float]:
        thermal_path = "/sys/class/thermal/thermal_zone0/temp"
        try:
            with open(thermal_path) as f:
                return int(f.read().strip()) / 1000.0
        except (OSError, ValueError):
            return None

    def _read_memory_usage(self) -> Optional[float]:
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            info: dict[str, int] = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    info[key] = int(parts[1])
            total = info.get("MemTotal", 0)
            available = info.get("MemAvailable", 0)
            if total <= 0:
                return None
            return (1.0 - available / total) * 100.0
        except (OSError, ValueError, KeyError):
            return None

    def _read_wifi_rssi(self) -> Optional[int]:
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

    def _read_disk_free(self) -> Optional[float]:
        try:
            stat = os.statvfs("/")
            free_bytes = stat.f_bavail * stat.f_frsize
            return free_bytes / (1024 * 1024 * 1024)
        except OSError:
            return None


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = HealthMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
