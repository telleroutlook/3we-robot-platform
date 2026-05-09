# SPDX-License-Identifier: Apache-2.0
"""
MQTT bridge node for fleet telemetry.

Subscribes to /diagnostics and forwards to an MQTT broker for
centralized monitoring (Grafana, InfluxDB, etc.).

Configuration via ROS2 parameters:
  - broker_url: MQTT broker URL (default: mqtt://localhost:1883)
  - username: MQTT username (default: empty)
  - password: MQTT password (default: empty)
  - topic_prefix: MQTT topic prefix (default: fleet/)
  - robot_id: Unique robot identifier (default: from namespace)
  - qos: MQTT QoS level 0/1/2 (default: 1)
"""

import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from diagnostic_msgs.msg import DiagnosticArray


class MqttBridgeNode(Node):

    def __init__(self) -> None:
        super().__init__('mqtt_bridge')

        self.declare_parameter('broker_url', 'mqtt://localhost:1883')
        self.declare_parameter('username', '')
        self.declare_parameter('password', '')
        self.declare_parameter('topic_prefix', 'fleet/')
        self.declare_parameter('robot_id', '')
        self.declare_parameter('qos', 1)

        self._broker_url = self.get_parameter('broker_url').value
        self._username = self.get_parameter('username').value
        self._password = self.get_parameter('password').value
        self._topic_prefix = self.get_parameter('topic_prefix').value
        self._robot_id = self.get_parameter('robot_id').value or self._get_default_robot_id()
        self._mqtt_qos = self.get_parameter('qos').value

        self._mqtt_client = None
        self._connected = False

        self._connect_mqtt()

        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=10,
        )
        self.create_subscription(
            DiagnosticArray, '/diagnostics', self._on_diagnostics, reliable_qos)

        self.create_timer(30.0, self._reconnect_check)

        self.get_logger().info(
            f'MQTT bridge started (broker={self._broker_url}, '
            f'topic={self._topic_prefix}{self._robot_id}/diagnostics)')

    def _get_default_robot_id(self) -> str:
        return self.get_namespace().strip('/') or 'robot'

    def _connect_mqtt(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self.get_logger().error(
                'paho-mqtt not installed. Install: pip install paho-mqtt')
            return

        url = self._broker_url.replace('mqtt://', '').replace('mqtts://', '')
        host_port = url.split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 1883

        self._mqtt_client = mqtt.Client(
            client_id=f'robot-{self._robot_id}',
            protocol=mqtt.MQTTv5,
        )

        if self._username:
            self._mqtt_client.username_pw_set(self._username, self._password)

        if self._broker_url.startswith('mqtts://'):
            self._mqtt_client.tls_set()

        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_disconnect = self._on_mqtt_disconnect

        try:
            self._mqtt_client.connect_async(host, port, keepalive=60)
            self._mqtt_client.loop_start()
        except Exception as e:
            self.get_logger().warn(f'MQTT connection failed: {e}')

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None) -> None:
        self._connected = True
        self.get_logger().info('MQTT connected')

    def _on_mqtt_disconnect(self, client, userdata, rc, properties=None) -> None:
        self._connected = False
        self.get_logger().warn(f'MQTT disconnected (rc={rc})')

    def _reconnect_check(self) -> None:
        if not self._connected and self._mqtt_client is not None:
            try:
                self._mqtt_client.reconnect()
            except Exception as exc:
                self.get_logger().warn(f'MQTT reconnect failed: {exc}')

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        if not self._connected or self._mqtt_client is None:
            return

        payload = {
            'timestamp': time.time(),
            'robot_id': self._robot_id,
            'status': [],
        }

        for status in msg.status:
            entry = {
                'name': status.name,
                'level': status.level,
                'message': status.message,
                'values': {kv.key: kv.value for kv in status.values},
            }
            payload['status'].append(entry)

        topic = f'{self._topic_prefix}{self._robot_id}/diagnostics'
        self._mqtt_client.publish(
            topic,
            json.dumps(payload),
            qos=self._mqtt_qos,
        )

    def destroy_node(self) -> None:
        if self._mqtt_client is not None:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MqttBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
