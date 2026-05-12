# SPDX-License-Identifier: Apache-2.0
"""Arm controller node — translates ArmCommand service calls into
PBC-34 I2C payload commands for the robotic arm and GPIO for the vacuum pump.

Service server: /collection/arm_command (ArmCommand)
Publishes:      /collection/arm_status (String)
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from robot_collection.constants import ArmState


class ArmControllerNode(Node):
    """Control the robotic arm + vacuum pump payload via PBC-34 bus."""

    def __init__(self) -> None:
        super().__init__("arm_controller")

        self.declare_parameter("pick_height_m", 0.02)
        self.declare_parameter("drop_height_m", 0.15)
        self.declare_parameter("vacuum_hold_time_s", 0.5)
        self.declare_parameter("payload_id", "arm-payload-01")

        self._state = ArmState.IDLE
        self._status_pub = self.create_publisher(String, "/collection/arm_status", 10)

        self._srv = None
        self._create_service()

        self._publish_status()
        self.get_logger().info("Arm controller started")

    def _create_service(self) -> None:
        try:
            from robot_interfaces.srv import ArmCommand

            self._srv = self.create_service(
                ArmCommand, "/collection/arm_command", self._handle_arm_command
            )
        except ImportError:
            self.get_logger().warn("robot_interfaces not available — service disabled")

    def _handle_arm_command(self, request, response):
        command = request.command.lower()
        self.get_logger().info(
            f"Arm command: {command} at ({request.target_x:.3f}, "
            f"{request.target_y:.3f}, {request.target_z:.3f})"
        )

        if command == "pick":
            response.success = self._execute_pick(
                request.target_x, request.target_y, request.target_z
            )
            response.message = "Pick complete" if response.success else "Pick failed"
        elif command == "retract":
            response.success = self._execute_retract()
            response.message = "Retracted" if response.success else "Retract failed"
        elif command == "home":
            response.success = self._execute_home()
            response.message = "Home" if response.success else "Home failed"
        else:
            response.success = False
            response.message = f"Unknown command: {command}"

        return response

    def _execute_pick(self, x: float, y: float, z: float) -> bool:
        self._set_state(ArmState.MOVING)

        if not self._move_to_position(x, y, z):
            self._set_state(ArmState.ERROR)
            return False

        if not self._vacuum_on():
            self._set_state(ArmState.ERROR)
            return False

        self._set_state(ArmState.HOLDING)

        drop_height = self.get_parameter("drop_height_m").value
        if not self._move_to_position(0.0, 0.0, drop_height):
            self._set_state(ArmState.ERROR)
            return False

        self._vacuum_off()
        self._set_state(ArmState.IDLE)
        return True

    def _execute_retract(self) -> bool:
        self._set_state(ArmState.MOVING)
        drop_height = self.get_parameter("drop_height_m").value
        success = self._move_to_position(0.0, 0.0, drop_height)
        self._set_state(ArmState.IDLE if success else ArmState.ERROR)
        return success

    def _execute_home(self) -> bool:
        self._set_state(ArmState.MOVING)
        self._vacuum_off()
        success = self._move_to_position(0.0, 0.0, 0.0)
        self._set_state(ArmState.IDLE if success else ArmState.ERROR)
        return success

    def _move_to_position(self, x: float, y: float, z: float) -> bool:
        self.get_logger().debug(f"Moving arm to ({x:.3f}, {y:.3f}, {z:.3f})")
        # TODO: Implement actual I2C communication with arm controller via PBC-34
        # For now, simulate successful movement
        return True

    def _vacuum_on(self) -> bool:
        self.get_logger().debug("Vacuum pump ON")
        # TODO: Implement GPIO control via PBC-34 payload bus
        return True

    def _vacuum_off(self) -> bool:
        self.get_logger().debug("Vacuum pump OFF")
        # TODO: Implement GPIO control via PBC-34 payload bus
        return True

    def _set_state(self, state: ArmState) -> None:
        self._state = state
        self._publish_status()

    def _publish_status(self) -> None:
        msg = String()
        msg.data = self._state.value
        self._status_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ArmControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
