# SPDX-License-Identifier: Apache-2.0
"""Generic webhook notification dispatcher for robot platform alerts.

Subscribes to /diagnostics, routes events by severity to configured webhook
endpoints with throttling, quiet hours, and HMAC signature support.
"""

import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Any

import rclpy
import yaml
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from rclpy.node import Node
from urllib.request import Request, urlopen
from urllib.error import URLError


class NotificationDispatcher(Node):
    def __init__(self) -> None:
        super().__init__("notification_dispatcher")

        self.declare_parameter("config_path", "")
        config_path = (
            self.get_parameter("config_path").get_parameter_value().string_value
        )

        self._config = self._load_config(config_path)
        self._recent_events: dict[str, float] = {}

        self.create_subscription(
            DiagnosticArray,
            "/diagnostics",
            self._on_diagnostics,
            10,
        )

        self.get_logger().info(
            f"Notification dispatcher started with {len(self._config.get('channels', []))} channel(s)"
        )

    def _load_config(self, path: str) -> dict[str, Any]:
        if not path or not os.path.isfile(path):
            self.get_logger().warn(f"Config not found at '{path}', using defaults")
            return {"channels": [], "throttling": {}, "templates": {}}

        with open(path) as f:
            raw = f.read()

        for key, val in os.environ.items():
            raw = raw.replace(f"${{{key}}}", val)

        return yaml.safe_load(raw) or {}

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        for status in msg.status:
            severity = self._level_to_severity(status.level)
            if severity is None:
                continue

            event = self._build_event(status, severity)

            if not self._should_dispatch(event):
                continue

            self._dispatch(event)

    def _level_to_severity(self, level: int) -> str | None:
        if level == DiagnosticStatus.ERROR:
            return "critical"
        if level == DiagnosticStatus.WARN:
            return "warning"
        return None

    def _build_event(self, status: DiagnosticStatus, severity: str) -> dict[str, Any]:
        values = {kv.key: kv.value for kv in status.values}
        return {
            "robot_id": os.environ.get("ROBOT_ID", "robot-001"),
            "event_type": status.name,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "details": status.message,
            "battery_percent": values.get("battery_percent", "N/A"),
        }

    def _should_dispatch(self, event: dict[str, Any]) -> bool:
        throttling = self._config.get("throttling", {})

        now = time.time()
        event_key = f"{event['event_type']}:{event['severity']}"
        window = throttling.get("duplicate_window_seconds", 60)
        last_sent = self._recent_events.get(event_key, 0)
        if now - last_sent < window:
            return False

        quiet = throttling.get("quiet_hours", {})
        if quiet:
            current_hour = datetime.now().hour
            start_hour = int(quiet.get("start", "22:00").split(":")[0])
            end_hour = int(quiet.get("end", "08:00").split(":")[0])
            allowed = quiet.get("allowed_levels", ["critical"])

            in_quiet = (
                start_hour > end_hour
                and (current_hour >= start_hour or current_hour < end_hour)
            ) or (start_hour < end_hour and start_hour <= current_hour < end_hour)
            if in_quiet and event["severity"] not in allowed:
                return False

        self._recent_events[event_key] = now
        return True

    def _dispatch(self, event: dict[str, Any]) -> None:
        for channel in self._config.get("channels", []):
            severity_filter = channel.get("severity_filter", ["critical", "warning"])
            if event["severity"] not in severity_filter:
                continue

            url = channel.get("url", "")
            if not url or url.startswith("${"):
                continue

            template_name = channel.get("template", "default")
            payload = self._format_payload(event, template_name)
            secret = channel.get("secret", "")

            self._send_webhook(url, payload, secret, channel.get("name", "unnamed"))

    def _format_payload(
        self, event: dict[str, Any], template_name: str
    ) -> dict[str, Any]:
        templates = self._config.get("templates", {})
        template = templates.get(template_name, {})

        safe_fields = {
            "severity": str(event.get("severity", "")),
            "event_type": str(event.get("event_type", "")),
            "robot_id": str(event.get("robot_id", "")),
            "details": str(event.get("details", "")),
            "timestamp": str(event.get("timestamp", "")),
            "battery_percent": str(event.get("battery_percent", "")),
        }

        title = template.get("title", "[{severity}] {event_type}").format_map(
            safe_fields
        )
        body = template.get("body", "{details}").format_map(safe_fields)

        return {
            "title": title,
            "body": body,
            "severity": event["severity"],
            "robot_id": event["robot_id"],
            "event_type": event["event_type"],
            "timestamp": event["timestamp"],
        }

    def _send_webhook(
        self, url: str, payload: dict[str, Any], secret: str, channel_name: str
    ) -> None:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        if secret and not secret.startswith("${"):
            signature = hmac.new(
                secret.encode("utf-8"), data, hashlib.sha256
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        def _do_send() -> None:
            try:
                req = Request(url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=10) as resp:
                    if resp.status < 300:
                        self.get_logger().debug(
                            f"Sent to {channel_name}: {payload['title']}"
                        )
                    else:
                        self.get_logger().warn(
                            f"Webhook {channel_name} returned {resp.status}"
                        )
            except URLError as e:
                self.get_logger().error(f"Webhook {channel_name} failed: {e}")
            except Exception as e:
                self.get_logger().error(f"Webhook {channel_name} unexpected error: {e}")

        import threading

        threading.Thread(target=_do_send, daemon=True).start()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NotificationDispatcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
