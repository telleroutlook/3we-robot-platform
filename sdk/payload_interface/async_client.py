# SPDX-License-Identifier: Apache-2.0
"""Async payload client bridging rclpy and asyncio for mission planning."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

try:
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
except ImportError as _err:
    raise ImportError(
        "rclpy is required for AsyncPayloadClient. "
        "Install with: pip install robot-payload-sdk[async] "
        "or ensure your ROS2 workspace is sourced."
    ) from _err

try:
    from nav2_msgs.action import NavigateToPose
    from geometry_msgs.msg import PoseStamped
    from rclpy.action import ActionClient
except ImportError:
    NavigateToPose = None
    PoseStamped = None
    ActionClient = None

try:
    from robot_interfaces.srv import EmergencyStop
except ImportError:
    EmergencyStop = None


@dataclass(frozen=True)
class BatteryState:
    """Immutable battery state snapshot."""

    voltage: float
    percentage: float
    state: str  # "ok", "low", "critical"


@dataclass(frozen=True)
class PayloadState:
    """Immutable payload state snapshot."""

    payload_id: str
    name: str
    connected: bool
    state: int


@dataclass(frozen=True)
class MissionResult:
    """Immutable mission execution result."""

    completed: int
    total: int
    success: bool
    failed_waypoint: Optional[int] = None


class AsyncPayloadClient:
    """Async client bridging rclpy and asyncio for mission planning.

    Uses a MultiThreadedExecutor running in a daemon thread to handle
    rclpy callbacks, with asyncio.Queue for thread-safe communication
    to the asyncio event loop.
    """

    def __init__(self, node_name: str = "async_payload_client") -> None:
        self._node_name = node_name
        self._node: Optional[Node] = None
        self._executor: Optional[MultiThreadedExecutor] = None
        self._spin_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected = False

    async def connect(self) -> None:
        """Initialize rclpy node and start executor in a daemon thread."""
        if self._connected:
            return

        self._loop = asyncio.get_running_loop()

        if not rclpy.ok():
            rclpy.init()

        self._node = rclpy.create_node(self._node_name)
        self._executor = MultiThreadedExecutor()
        self._executor.add_node(self._node)

        self._spin_thread = threading.Thread(
            target=self._executor.spin,
            daemon=True,
            name=f"{self._node_name}_executor",
        )
        self._spin_thread.start()
        self._connected = True

    async def disconnect(self) -> None:
        """Shutdown executor and destroy the node."""
        if not self._connected:
            return

        self._connected = False

        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

        if self._spin_thread is not None:
            self._spin_thread.join(timeout=5.0)
            self._spin_thread = None

        if self._node is not None:
            self._node.destroy_node()
            self._node = None

    async def subscribe_topic(
        self, topic: str, msg_type: type, qos: int = 10
    ) -> AsyncIterator:
        """Subscribe to a ROS2 topic and yield messages as an async iterator.

        Args:
            topic: ROS2 topic name.
            msg_type: ROS2 message type class.
            qos: QoS depth (default 10).

        Yields:
            Messages received on the topic.
        """
        self._ensure_connected()
        assert self._node is not None
        assert self._loop is not None

        queue: asyncio.Queue[Any] = asyncio.Queue()

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=qos,
        )

        def _callback(msg: Any) -> None:
            self._loop.call_soon_threadsafe(queue.put_nowait, msg)

        subscription = self._node.create_subscription(
            msg_type, topic, _callback, qos_profile
        )

        try:
            while self._connected:
                msg = await queue.get()
                yield msg
        finally:
            self._node.destroy_subscription(subscription)

    async def call_service(
        self, service_name: str, srv_type: type, request: Any, timeout: float = 5.0
    ) -> Any:
        """Call a ROS2 service asynchronously.

        Args:
            service_name: Fully qualified service name.
            srv_type: ROS2 service type class.
            request: Service request message.
            timeout: Seconds to wait for the service response.

        Returns:
            Service response message.

        Raises:
            TimeoutError: If service does not respond within timeout.
            RuntimeError: If service is not available.
        """
        self._ensure_connected()
        assert self._node is not None
        assert self._loop is not None

        client = self._node.create_client(srv_type, service_name)

        try:
            if not client.wait_for_service(timeout_sec=timeout):
                raise RuntimeError(
                    f"Service '{service_name}' not available after {timeout}s"
                )

            future = client.call_async(request)
            asyncio_future: asyncio.Future[Any] = self._loop.create_future()

            def _done_callback(rclpy_future: Any) -> None:
                exc = rclpy_future.exception()
                if exc is not None:
                    self._loop.call_soon_threadsafe(asyncio_future.set_exception, exc)
                else:
                    result = rclpy_future.result()
                    self._loop.call_soon_threadsafe(asyncio_future.set_result, result)

            future.add_done_callback(_done_callback)

            return await asyncio.wait_for(asyncio_future, timeout=timeout)
        finally:
            self._node.destroy_client(client)

    async def send_nav_goal(
        self, x: float, y: float, theta: float = 0.0, timeout: float = 60.0
    ) -> bool:
        """Send a navigation goal using NavigateToPose action.

        Args:
            x: Target x position in meters.
            y: Target y position in meters.
            theta: Target orientation in radians.
            timeout: Seconds to wait for goal completion.

        Returns:
            True if navigation succeeded, False otherwise.
        """
        self._ensure_connected()
        assert self._node is not None
        assert self._loop is not None

        if NavigateToPose is None or PoseStamped is None or ActionClient is None:
            raise ImportError(
                "nav2_msgs and geometry_msgs are required for navigation goals."
            )

        action_client = ActionClient(self._node, NavigateToPose, "navigate_to_pose")

        if not action_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("NavigateToPose action server not available")

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self._node.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        import math

        goal_msg.pose.pose.orientation.z = math.sin(theta / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(theta / 2.0)

        asyncio_future: asyncio.Future[bool] = self._loop.create_future()

        send_goal_future = action_client.send_goal_async(goal_msg)

        def _goal_response_callback(future: Any) -> None:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self._loop.call_soon_threadsafe(asyncio_future.set_result, False)
                return

            result_future = goal_handle.get_result_async()

            def _result_callback(result_future: Any) -> None:
                result = result_future.result()
                success = result.status == 4  # STATUS_SUCCEEDED
                self._loop.call_soon_threadsafe(asyncio_future.set_result, success)

            result_future.add_done_callback(_result_callback)

        send_goal_future.add_done_callback(_goal_response_callback)

        try:
            return await asyncio.wait_for(asyncio_future, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        finally:
            action_client.destroy()

    async def execute_mission(
        self, waypoints: list[tuple[float, float, float]]
    ) -> MissionResult:
        """Execute a mission by navigating through a sequence of waypoints.

        Stops on first failure and reports which waypoint failed.

        Args:
            waypoints: List of (x, y, theta) tuples.

        Returns:
            MissionResult with completion details.
        """
        total = len(waypoints)

        for idx, (x, y, theta) in enumerate(waypoints):
            success = await self.send_nav_goal(x, y, theta)
            if not success:
                return MissionResult(
                    completed=idx,
                    total=total,
                    success=False,
                    failed_waypoint=idx,
                )

        return MissionResult(completed=total, total=total, success=True)

    async def trigger_estop(self, reason: str = "SDK triggered") -> bool:
        """Trigger emergency stop via the EmergencyStop service.

        Args:
            reason: Human-readable reason for the e-stop.

        Returns:
            True if e-stop was acknowledged, False otherwise.
        """
        self._ensure_connected()

        if EmergencyStop is None:
            raise ImportError(
                "robot_interfaces.srv.EmergencyStop is required for e-stop."
            )

        request = EmergencyStop.Request()
        request.reason = reason

        response = await self.call_service(
            "/emergency_stop", EmergencyStop, request, timeout=2.0
        )
        return bool(response.success)

    async def get_battery_state(self) -> BatteryState:
        """Get current battery state (subscribes, takes first message, unsubscribes).

        Returns:
            BatteryState snapshot.
        """
        self._ensure_connected()
        assert self._node is not None
        assert self._loop is not None

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)

        from sensor_msgs.msg import BatteryState as RosBatteryState

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        def _callback(msg: Any) -> None:
            self._loop.call_soon_threadsafe(queue.put_nowait, msg)

        subscription = self._node.create_subscription(
            RosBatteryState, "/battery_state", _callback, qos_profile
        )

        try:
            msg = await asyncio.wait_for(queue.get(), timeout=5.0)
            percentage = msg.percentage
            if percentage > 0.2:
                state = "ok"
            elif percentage > 0.1:
                state = "low"
            else:
                state = "critical"

            return BatteryState(
                voltage=msg.voltage,
                percentage=percentage,
                state=state,
            )
        finally:
            self._node.destroy_subscription(subscription)

    async def get_payload_state(self) -> PayloadState:
        """Get current payload state (subscribes, takes first message, unsubscribes).

        Returns:
            PayloadState snapshot.
        """
        self._ensure_connected()
        assert self._node is not None
        assert self._loop is not None

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)

        # Use a generic message type; actual type depends on robot_interfaces
        from std_msgs.msg import String

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        def _callback(msg: Any) -> None:
            self._loop.call_soon_threadsafe(queue.put_nowait, msg)

        subscription = self._node.create_subscription(
            String, "/payload/state", _callback, qos_profile
        )

        try:
            msg = await asyncio.wait_for(queue.get(), timeout=5.0)
            return PayloadState(
                payload_id=getattr(msg, "payload_id", "unknown"),
                name=getattr(msg, "name", "unknown"),
                connected=getattr(msg, "connected", False),
                state=getattr(msg, "state", 0),
            )
        finally:
            self._node.destroy_subscription(subscription)

    async def __aenter__(self) -> "AsyncPayloadClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def _ensure_connected(self) -> None:
        """Raise if client is not connected."""
        if not self._connected or self._node is None:
            raise RuntimeError(
                "Client is not connected. Call connect() or use async with."
            )
