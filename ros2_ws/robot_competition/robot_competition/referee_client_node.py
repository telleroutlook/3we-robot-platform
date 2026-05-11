# SPDX-License-Identifier: Apache-2.0
"""Referee system client for RoboCup Logistics League."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RefereeClientNode(Node):
    """Connects to the RCLL referee box via TCP and publishes game state."""

    def __init__(self):
        super().__init__("referee_client")
        self.declare_parameter("referee_host", "192.168.1.1")
        self.declare_parameter("referee_port", 4444)
        self.declare_parameter("team_name", "3WE")

        self.game_state_pub = self.publisher(String, "/competition/game_state", 10)
        self.order_pub = self.publisher(String, "/competition/orders", 10)

        # TODO: Implement TCP/gRPC connection to referee box
        # TODO: Parse protobuf messages from referee system
        # TODO: Publish game phase transitions (SETUP, EXPLORATION, PRODUCTION)
        # TODO: Forward order assignments to task_executor

        self.get_logger().info("Referee client node initialized (stub)")

    def publisher(self, msg_type, topic, qos):
        return self.create_publisher(msg_type, topic, qos)


def main(args=None):
    rclpy.init(args=args)
    node = RefereeClientNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
