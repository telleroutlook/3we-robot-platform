# SPDX-License-Identifier: Apache-2.0
"""Shared ROS2 node logic for Gazebo and Real backends.

Encapsulates all rclpy subscriptions, publishers, and action clients
so that both backends share a single implementation of ROS2 communication.
"""

from __future__ import annotations

import math
import threading
import time
from typing import TYPE_CHECKING

import numpy as np

from threewe.types import (
    BatteryState,
    CameraIntrinsics,
    ExploreResult,
    IMUData,
    LaserScan,
    MoveResult,
    OccupancyGrid,
    Pose2D,
    RGBDImage,
    Velocity,
)

if TYPE_CHECKING:
    from threewe.config import RobotConfig


def _euler_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    """Extract yaw (theta) from quaternion."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class ROS2Node:
    """Manages a ROS2 node with topic subscriptions and publishers."""

    def __init__(self, node_name: str, config: RobotConfig) -> None:
        self._config = config
        self._node_name = node_name
        self._node = None
        self._spin_thread: threading.Thread | None = None
        self._running = False

        self._latest_image: np.ndarray | None = None
        self._latest_depth: np.ndarray | None = None
        self._latest_scan: LaserScan | None = None
        self._latest_pose: Pose2D = Pose2D()
        self._latest_velocity: Velocity = Velocity()
        self._latest_imu: IMUData | None = None
        self._latest_battery: BatteryState = BatteryState()
        self._latest_map: OccupancyGrid | None = None
        self._latest_wheel_speeds: np.ndarray = np.zeros(4, dtype=np.float32)
        self._latest_motor_current: np.ndarray = np.zeros(4, dtype=np.float32)
        self._state_lock = threading.Lock()

        self._cmd_vel_pub = None
        self._nav_action_client = None

    def connect(self) -> None:
        import rclpy
        from rclpy.qos import (
            QoSDurabilityPolicy,
            QoSHistoryPolicy,
            QoSProfile,
            QoSReliabilityPolicy,
        )

        if not rclpy.ok():
            rclpy.init()

        self._node = rclpy.create_node(self._node_name)

        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        reliable_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        from geometry_msgs.msg import Twist
        from nav_msgs.msg import OccupancyGrid as OccupancyGridMsg
        from nav_msgs.msg import Odometry
        from sensor_msgs.msg import BatteryState as BatteryStateMsg
        from sensor_msgs.msg import Image, Imu
        from sensor_msgs.msg import LaserScan as LaserScanMsg

        self._node.create_subscription(Image, "/camera/image_raw", self._image_callback, sensor_qos)
        self._node.create_subscription(
            Image, "/camera/depth/image_raw", self._depth_callback, sensor_qos
        )
        self._node.create_subscription(LaserScanMsg, "/scan", self._scan_callback, sensor_qos)
        self._node.create_subscription(Odometry, "/odom", self._odom_callback, sensor_qos)
        self._node.create_subscription(Imu, "/imu/data", self._imu_callback, sensor_qos)
        self._node.create_subscription(OccupancyGridMsg, "/map", self._map_callback, reliable_qos)
        self._node.create_subscription(
            BatteryStateMsg, "/battery_state", self._battery_callback, sensor_qos
        )

        try:
            from std_msgs.msg import Float32MultiArray

            self._node.create_subscription(
                Float32MultiArray, "/wheel_speeds", self._wheel_speeds_callback, sensor_qos
            )
            self._node.create_subscription(
                Float32MultiArray, "/motor_current", self._motor_current_callback, sensor_qos
            )
        except ImportError:
            pass

        self._cmd_vel_pub = self._node.create_publisher(Twist, "/cmd_vel", reliable_qos)

        try:
            from nav2_msgs.action import NavigateToPose
            from rclpy.action import ActionClient

            self._nav_action_client = ActionClient(self._node, NavigateToPose, "navigate_to_pose")
        except ImportError:
            self._nav_action_client = None

        self._running = True
        self._spin_thread = threading.Thread(target=self._spin, daemon=True)
        self._spin_thread.start()

    def _spin(self) -> None:
        import rclpy

        while self._running and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.01)

    def disconnect(self) -> None:
        self._running = False
        if self._spin_thread is not None:
            self._spin_thread.join(timeout=2.0)
            self._spin_thread = None
        if self._node is not None:
            self._node.destroy_node()
            self._node = None

    @property
    def is_connected(self) -> bool:
        return self._node is not None and self._running

    def _image_callback(self, msg) -> None:
        h, w = msg.height, msg.width
        if msg.encoding == "bgr8":
            img = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3).copy()
            image = img[:, :, ::-1]
        elif msg.encoding == "rgb8":
            image = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3).copy()
        else:
            import logging

            logging.getLogger(__name__).warning(
                "Unknown image encoding %s, attempting raw parse", msg.encoding
            )
            image = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3).copy()
        with self._state_lock:
            self._latest_image = image

    def _depth_callback(self, msg) -> None:
        h, w = msg.height, msg.width
        if msg.encoding == "32FC1":
            depth = np.frombuffer(msg.data, dtype=np.float32).reshape(h, w)
        elif msg.encoding == "16UC1":
            raw = np.frombuffer(msg.data, dtype=np.uint16).reshape(h, w)
            depth = raw.astype(np.float32) / 1000.0
        else:
            import logging

            logging.getLogger(__name__).warning(
                "Unknown depth encoding %s, skipping frame", msg.encoding
            )
            return
        with self._state_lock:
            self._latest_depth = depth

    def _scan_callback(self, msg) -> None:
        ranges = np.array(msg.ranges, dtype=np.float32)
        n = len(ranges)
        angles = np.linspace(msg.angle_min, msg.angle_max, n, dtype=np.float32)
        scan = LaserScan(
            ranges=ranges,
            angles=angles,
            angle_min=msg.angle_min,
            angle_max=msg.angle_max,
            range_max=msg.range_max,
            timestamp=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
        )
        with self._state_lock:
            self._latest_scan = scan

    def _odom_callback(self, msg) -> None:
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        theta = _euler_from_quaternion(ori.x, ori.y, ori.z, ori.w)
        pose = Pose2D(x=pos.x, y=pos.y, theta=theta)
        twist = msg.twist.twist
        velocity = Velocity(vx=twist.linear.x, vy=twist.linear.y, omega=twist.angular.z)
        with self._state_lock:
            self._latest_pose = pose
            self._latest_velocity = velocity

    def _imu_callback(self, msg) -> None:
        acc = msg.linear_acceleration
        gyro = msg.angular_velocity
        ori = msg.orientation
        imu = IMUData(
            acceleration=np.array([acc.x, acc.y, acc.z], dtype=np.float32),
            angular_velocity=np.array([gyro.x, gyro.y, gyro.z], dtype=np.float32),
            orientation=np.array([ori.x, ori.y, ori.z, ori.w], dtype=np.float32),
            timestamp=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
        )
        with self._state_lock:
            self._latest_imu = imu

    def _battery_callback(self, msg) -> None:
        from sensor_msgs.msg import BatteryState as BatteryStateMsg

        battery = BatteryState(
            voltage=msg.voltage,
            percentage=msg.percentage,
            is_charging=msg.power_supply_status == BatteryStateMsg.POWER_SUPPLY_STATUS_CHARGING,
        )
        with self._state_lock:
            self._latest_battery = battery

    def _map_callback(self, msg) -> None:
        w, h = msg.info.width, msg.info.height
        data = np.array(msg.data, dtype=np.int8).reshape(h, w)
        origin_pos = msg.info.origin.position
        origin_ori = msg.info.origin.orientation
        theta = _euler_from_quaternion(origin_ori.x, origin_ori.y, origin_ori.z, origin_ori.w)
        grid = OccupancyGrid(
            data=data,
            resolution=msg.info.resolution,
            origin=Pose2D(x=origin_pos.x, y=origin_pos.y, theta=theta),
        )
        with self._state_lock:
            self._latest_map = grid

    def _wheel_speeds_callback(self, msg) -> None:
        data = np.array(msg.data, dtype=np.float32)
        if data.shape[0] >= 4:
            with self._state_lock:
                self._latest_wheel_speeds = data[:4]

    def _motor_current_callback(self, msg) -> None:
        data = np.array(msg.data, dtype=np.float32)
        if data.shape[0] >= 4:
            with self._state_lock:
                self._latest_motor_current = data[:4]

    def get_camera_image(self) -> np.ndarray:
        with self._state_lock:
            image = self._latest_image
        if image is not None:
            return image
        h, w = self._config.api.image_size[1], self._config.api.image_size[0]
        return np.zeros((h, w, 3), dtype=np.uint8)

    def get_rgbd_image(self) -> RGBDImage:
        with self._state_lock:
            image = self._latest_image
            depth = self._latest_depth
        rgb = (
            image
            if image is not None
            else np.zeros(
                (self._config.api.image_size[1], self._config.api.image_size[0], 3), dtype=np.uint8
            )
        )
        h, w = rgb.shape[0], rgb.shape[1]
        depth = depth if depth is not None else np.zeros((h, w), dtype=np.float32)
        return RGBDImage(
            rgb=rgb,
            depth=depth,
            intrinsics=CameraIntrinsics(width=w, height=h),
            timestamp=time.time(),
        )

    def get_lidar_scan(self) -> LaserScan:
        with self._state_lock:
            scan = self._latest_scan
        if scan is not None:
            return scan
        n = self._config.api.lidar_points
        return LaserScan(
            ranges=np.zeros(n, dtype=np.float32),
            angles=np.linspace(0, 2 * np.pi, n, dtype=np.float32),
            angle_min=0.0,
            angle_max=2 * np.pi,
            range_max=12.0,
        )

    def get_pose(self) -> Pose2D:
        with self._state_lock:
            return self._latest_pose

    def get_velocity(self) -> Velocity:
        with self._state_lock:
            return self._latest_velocity

    def get_imu(self) -> IMUData:
        with self._state_lock:
            imu = self._latest_imu
        if imu is not None:
            return imu
        return IMUData(
            acceleration=np.array([0.0, 0.0, 9.81], dtype=np.float32),
            angular_velocity=np.zeros(3, dtype=np.float32),
            orientation=np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        )

    def get_battery_state(self) -> BatteryState:
        with self._state_lock:
            return self._latest_battery

    def get_map(self) -> OccupancyGrid:
        with self._state_lock:
            grid = self._latest_map
        if grid is not None:
            return grid
        return OccupancyGrid(data=np.full((100, 100), -1, dtype=np.int8))

    def get_wheel_speeds(self) -> np.ndarray:
        with self._state_lock:
            return self._latest_wheel_speeds.copy()

    def get_motor_current(self) -> np.ndarray:
        with self._state_lock:
            return self._latest_motor_current.copy()

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        if self._cmd_vel_pub is None:
            import logging

            logging.getLogger(__name__).warning(
                "set_velocity called but cmd_vel publisher not ready"
            )
            return
        from geometry_msgs.msg import Twist

        msg = Twist()
        msg.linear.x = vx
        msg.linear.y = vy
        msg.angular.z = omega
        self._cmd_vel_pub.publish(msg)

    def stop(self) -> None:
        self.set_velocity(0.0, 0.0, 0.0)

    async def move_to(
        self, x: float, y: float, theta: float | None = None, timeout: float = 60.0
    ) -> MoveResult:
        if self._nav_action_client is None:
            return MoveResult(
                success=False,
                final_pose=self._latest_pose,
                reason="nav2_msgs not available",
            )

        import asyncio

        from geometry_msgs.msg import PoseStamped
        from nav2_msgs.action import NavigateToPose

        if not self._nav_action_client.wait_for_server(timeout_sec=5.0):
            return MoveResult(
                success=False,
                final_pose=self._latest_pose,
                reason="Nav2 server not available",
            )

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        if theta is not None:
            goal.pose.pose.orientation.z = math.sin(theta / 2.0)
            goal.pose.pose.orientation.w = math.cos(theta / 2.0)
        else:
            goal.pose.pose.orientation.w = 1.0

        start_time = time.time()
        start_pose = self._latest_pose

        future = self._nav_action_client.send_goal_async(goal)
        while not future.done():
            await asyncio.sleep(0.1)
            if time.time() - start_time > timeout:
                return MoveResult(
                    success=False,
                    final_pose=self._latest_pose,
                    duration=time.time() - start_time,
                    reason="timeout",
                )

        goal_handle = future.result()
        if not goal_handle.accepted:
            return MoveResult(
                success=False,
                final_pose=self._latest_pose,
                reason="goal_rejected",
            )

        result_future = goal_handle.get_result_async()
        while not result_future.done():
            await asyncio.sleep(0.1)
            if time.time() - start_time > timeout:
                goal_handle.cancel_goal_async()
                return MoveResult(
                    success=False,
                    final_pose=self._latest_pose,
                    duration=time.time() - start_time,
                    reason="timeout",
                )

        duration = time.time() - start_time
        final_pose = self._latest_pose
        dx = final_pose.x - start_pose.x
        dy = final_pose.y - start_pose.y
        distance = math.sqrt(dx * dx + dy * dy)

        return MoveResult(
            success=True,
            final_pose=final_pose,
            duration=duration,
            distance=distance,
            reason="reached",
        )

    async def move_forward(self, distance: float) -> MoveResult:
        """Drive forward using velocity commands for the specified distance."""
        import asyncio

        speed = min(abs(distance) * 0.5, self._config.limits.max_linear_velocity * 0.5)
        if speed < 0.01:
            return MoveResult(success=True, final_pose=self._latest_pose, reason="reached")

        direction = 1.0 if distance >= 0 else -1.0
        timeout = abs(distance) / speed * 3.0
        start_time = time.time()
        with self._state_lock:
            start_pose = self._latest_pose
        traveled = 0.0

        while traveled < abs(distance):
            if time.time() - start_time > timeout:
                self.stop()
                with self._state_lock:
                    final_pose = self._latest_pose
                return MoveResult(
                    success=False,
                    final_pose=final_pose,
                    distance=traveled,
                    reason="timeout",
                )
            self.set_velocity(direction * speed, 0.0, 0.0)
            await asyncio.sleep(0.05)
            with self._state_lock:
                current_pose = self._latest_pose
            dx = current_pose.x - start_pose.x
            dy = current_pose.y - start_pose.y
            traveled = math.sqrt(dx * dx + dy * dy)

        self.stop()
        with self._state_lock:
            final_pose = self._latest_pose
        return MoveResult(
            success=True,
            final_pose=final_pose,
            distance=traveled,
            reason="reached",
        )

    async def rotate(self, angle: float) -> MoveResult:
        """Rotate in place by the specified angle."""
        import asyncio

        speed = min(abs(angle) * 0.5, self._config.limits.max_angular_velocity * 0.5)
        if speed < 0.01:
            return MoveResult(success=True, final_pose=self._latest_pose, reason="reached")

        direction = 1.0 if angle >= 0 else -1.0
        timeout = abs(angle) / speed * 3.0
        start_time = time.time()
        with self._state_lock:
            start_theta = self._latest_pose.theta
        rotated = 0.0

        while rotated < abs(angle):
            if time.time() - start_time > timeout:
                self.stop()
                with self._state_lock:
                    final_pose = self._latest_pose
                return MoveResult(
                    success=False,
                    final_pose=final_pose,
                    reason="timeout",
                )
            self.set_velocity(0.0, 0.0, direction * speed)
            await asyncio.sleep(0.05)
            with self._state_lock:
                current_theta = self._latest_pose.theta
            diff = current_theta - start_theta
            rotated = abs(math.atan2(math.sin(diff), math.cos(diff)))

        self.stop()
        with self._state_lock:
            final_pose = self._latest_pose
        return MoveResult(
            success=True,
            final_pose=final_pose,
            reason="reached",
        )

    async def follow_path(self, waypoints: list) -> MoveResult:
        """Follow a sequence of waypoints by calling move_to for each."""
        if not waypoints:
            return MoveResult(success=True, final_pose=self._latest_pose, reason="reached")

        total_distance = 0.0
        start_time = time.time()

        for wp in waypoints:
            result = await self.move_to(wp.x, wp.y, wp.theta)
            total_distance += result.distance or 0.0
            if not result.success:
                return MoveResult(
                    success=False,
                    final_pose=self._latest_pose,
                    duration=time.time() - start_time,
                    distance=total_distance,
                    reason=result.reason,
                )

        return MoveResult(
            success=True,
            final_pose=self._latest_pose,
            duration=time.time() - start_time,
            distance=total_distance,
            reason="reached",
        )

    async def explore(self, timeout: float = 60.0) -> ExploreResult:
        """Autonomous exploration stub — samples map coverage over a 1-second window only.

        Does not issue any navigation commands. Implement frontier-based exploration
        via Nav2 explore_lite for real behavior.
        """
        import asyncio

        start_time = time.time()
        start_map = self.get_map()
        start_explored = int(np.sum(start_map.data >= 0))

        await asyncio.sleep(min(timeout, 1.0))

        end_map = self.get_map()
        total_cells = end_map.data.size
        explored_cells = int(np.sum(end_map.data >= 0))
        new_cells = explored_cells - start_explored
        coverage = explored_cells / total_cells if total_cells > 0 else 0.0
        duration = time.time() - start_time

        return ExploreResult(
            coverage=coverage,
            duration=duration,
            cells_explored=new_cells,
            timed_out=duration >= timeout,
        )
