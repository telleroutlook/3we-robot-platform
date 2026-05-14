# SPDX-License-Identifier: Apache-2.0
"""Task executor using BehaviorTree.CPP for RCLL order fulfillment."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TaskExecutorNode(Node):
    """Executes competition tasks via behavior tree state machine."""

    def __init__(self):
        super().__init__("task_executor")
        self.declare_parameter("bt_xml_path", "")
        self.declare_parameter("max_concurrent_orders", 2)

        self.status_pub = self.create_publisher(String, "/competition/task_status", 10)

        self.create_subscription(
            String, "/competition/orders", self._order_callback, 10
        )

        self.get_logger().warn("Task executor node awaiting implementation")

    def _order_callback(self, msg):
        self.get_logger().info(f"Received order: {msg.data}")


def main(args=None):
    rclpy.init(args=args)
    node = TaskExecutorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
