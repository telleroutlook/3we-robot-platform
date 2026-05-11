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

            payload = self._format_for_channel(event, channel)
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

    def _format_for_channel(
        self, event: dict[str, Any], channel: dict[str, Any]
    ) -> dict[str, Any]:
        """Format payload based on channel type (dingtalk, feishu, slack, or generic)."""
        channel_type = channel.get("type", "webhook")
        template_name = channel.get("template", "default")
        base_payload = self._format_payload(event, template_name)

        if channel_type == "dingtalk":
            return self._format_dingtalk(base_payload, channel)
        elif channel_type == "feishu":
            return self._format_feishu(base_payload, channel)
        elif channel_type == "slack":
            return self._format_slack(base_payload, channel)
        return base_payload

    def _format_dingtalk(
        self, payload: dict[str, Any], channel: dict[str, Any]
    ) -> dict[str, Any]:
        """Format as DingTalk actionCard message."""
        severity = payload["severity"]
        color_map = {"critical": "#FF0000", "warning": "#FFA500"}
        color = color_map.get(severity, "#333333")
        dashboard_url = channel.get("dashboard_url", "")

        markdown_body = (
            f"### {payload['title']}\n\n"
            f"**Robot:** {payload['robot_id']}  \n"
            f"**Event:** {payload['event_type']}  \n"
            f"**Time:** {payload['timestamp']}  \n\n"
            f"{payload['body']}"
        )

        action_card: dict[str, Any] = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": payload["title"],
                "text": markdown_body,
                "hideAvatar": "0",
                "btnOrientation": "0",
            },
        }

        if dashboard_url:
            action_card["actionCard"]["btns"] = [
                {"title": "View Dashboard", "actionURL": dashboard_url},
                {"title": "Acknowledge", "actionURL": f"{dashboard_url}/ack"},
            ]
        else:
            action_card["actionCard"]["singleTitle"] = "View Details"
            action_card["actionCard"]["singleURL"] = ""

        return action_card

    def _format_feishu(
        self, payload: dict[str, Any], channel: dict[str, Any]
    ) -> dict[str, Any]:
        """Format as Feishu (Lark) interactive card message."""
        severity = payload["severity"]
        color_map = {"critical": "red", "warning": "orange"}
        template_color = color_map.get(severity, "blue")

        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": payload["title"]},
                    "template": template_color,
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Robot:** {payload['robot_id']}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Severity:** {severity.upper()}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Event:** {payload['event_type']}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Time:** {payload['timestamp']}",
                                },
                            },
                        ],
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": payload["body"],
                        },
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "Acknowledge",
                                },
                                "type": "primary",
                                "value": {
                                    "action": "ack",
                                    "robot_id": payload["robot_id"],
                                },
                            }
                        ],
                    },
                ],
            },
        }

    def _format_slack(
        self, payload: dict[str, Any], channel: dict[str, Any]
    ) -> dict[str, Any]:
        """Format as Slack Block Kit message."""
        severity = payload["severity"]
        emoji_map = {"critical": ":red_circle:", "warning": ":warning:"}
        emoji = emoji_map.get(severity, ":information_source:")

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {payload['title']}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Robot:*\n{payload['robot_id']}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{severity.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Event:*\n{payload['event_type']}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{payload['timestamp']}",
                        },
                    ],
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": payload["body"]},
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Acknowledge"},
                            "style": "primary",
                            "action_id": "ack_alert",
                            "value": payload["robot_id"],
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Dashboard"},
                            "url": channel.get("dashboard_url", ""),
                            "action_id": "view_dashboard",
                        },
                    ],
                },
            ],
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
