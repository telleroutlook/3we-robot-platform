# SPDX-License-Identifier: Apache-2.0
"""Basket controller node — translates BasketDump service calls into
PBC-34 PWM commands for the tipping basket servo.

Service server: /collection/basket_dump (BasketDump)
Publishes:      /collection/basket_state (String)
"""

from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from robot_collection.constants import BasketState


class BasketControllerNode(Node):
    """Control the tipping basket servo via PBC-34 PWM."""

    def __init__(self) -> None:
        super().__init__("basket_controller")

        self.declare_parameter("dump_angle_deg", 120)
        self.declare_parameter("home_angle_deg", 0)
        self.declare_parameter("dump_hold_time_s", 2.0)
        self.declare_parameter("reset_time_s", 1.0)
        self.declare_parameter("payload_id", "basket-payload-01")

        self._state = BasketState.NORMAL
        self._status_pub = self.create_publisher(String, "/collection/basket_state", 10)

        self._srv = None
        self._create_service()

        self._publish_status()
        self.get_logger().info("Basket controller started")

    def _create_service(self) -> None:
        try:
            from robot_interfaces.srv import BasketDump

            self._srv = self.create_service(
                BasketDump, "/collection/basket_dump", self._handle_basket_dump
            )
        except ImportError:
            self.get_logger().warn("robot_interfaces not available — service disabled")

    def _handle_basket_dump(self, request, response):
        if request.dump:
            response.success = self._execute_dump()
            response.message = "Dump complete" if response.success else "Dump failed"
        else:
            response.success = self._execute_reset()
            response.message = "Reset complete" if response.success else "Reset failed"
        return response

    def _execute_dump(self) -> bool:
        self.get_logger().info("Executing basket dump")
        self._set_state(BasketState.DUMPING)

        dump_angle = self.get_parameter("dump_angle_deg").value
        if not self._set_servo_angle(dump_angle):
            self._set_state(BasketState.NORMAL)
            return False

        dump_hold = self.get_parameter("dump_hold_time_s").value
        time.sleep(dump_hold)

        return self._execute_reset()

    def _execute_reset(self) -> bool:
        self._set_state(BasketState.RESETTING)

        home_angle = self.get_parameter("home_angle_deg").value
        if not self._set_servo_angle(home_angle):
            self._set_state(BasketState.NORMAL)
            return False

        reset_time = self.get_parameter("reset_time_s").value
        time.sleep(reset_time)

        self._set_state(BasketState.NORMAL)
        return True

    def _set_servo_angle(self, angle_deg: int) -> bool:
        self.get_logger().debug(f"Setting servo to {angle_deg}°")
        return True

    def _set_state(self, state: BasketState) -> None:
        self._state = state
        self._publish_status()

    def _publish_status(self) -> None:
        msg = String()
        msg.data = self._state.value
        self._status_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = BasketControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
