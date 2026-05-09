# SPDX-License-Identifier: Apache-2.0
"""Tests for AsyncPayloadClient using mocked rclpy."""

from __future__ import annotations

import asyncio
import importlib
import sys
from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock rclpy and related ROS2 packages before importing async_client
# ---------------------------------------------------------------------------

_mock_rclpy = MagicMock()
_mock_rclpy.ok.return_value = True
_mock_rclpy.init = MagicMock()
_mock_rclpy.create_node = MagicMock()

_mock_executors = MagicMock()
_mock_node = MagicMock()
_mock_qos = MagicMock()
_mock_action = MagicMock()

_mock_nav2 = MagicMock()
_mock_geometry = MagicMock()
_mock_robot_interfaces = MagicMock()

# Install mocks into sys.modules so import succeeds
_rclpy_mocks = {
    "rclpy": _mock_rclpy,
    "rclpy.executors": _mock_executors,
    "rclpy.node": _mock_node,
    "rclpy.qos": _mock_qos,
    "rclpy.action": _mock_action,
    "nav2_msgs": _mock_nav2,
    "nav2_msgs.action": _mock_nav2.action,
    "geometry_msgs": _mock_geometry,
    "geometry_msgs.msg": _mock_geometry.msg,
    "robot_interfaces": _mock_robot_interfaces,
    "robot_interfaces.srv": _mock_robot_interfaces.srv,
    "sensor_msgs": MagicMock(),
    "sensor_msgs.msg": MagicMock(),
    "std_msgs": MagicMock(),
    "std_msgs.msg": MagicMock(),
}


@pytest.fixture(autouse=True)
def _install_rclpy_mocks() -> Any:
    """Install rclpy mocks for all tests, clean up module cache after."""
    with patch.dict(sys.modules, _rclpy_mocks):
        # Clear cached async_client module to force re-import with mocks
        mods_to_clear = [k for k in sys.modules if "async_client" in k]
        for mod in mods_to_clear:
            del sys.modules[mod]
        yield
    # Clean up after test
    mods_to_clear = [k for k in sys.modules if "async_client" in k]
    for mod in mods_to_clear:
        del sys.modules[mod]


def _import_async_client() -> Any:
    """Import async_client module with mocks active."""
    return importlib.import_module("payload_interface.async_client")


# ---------------------------------------------------------------------------
# Dataclass immutability and field tests
# ---------------------------------------------------------------------------


class TestMissionResult:
    def test_mission_result_frozen(self) -> None:
        mod = _import_async_client()
        result = mod.MissionResult(
            completed=3, total=5, success=False, failed_waypoint=3
        )
        with pytest.raises(FrozenInstanceError):
            result.completed = 10  # type: ignore[misc]

    def test_mission_result_defaults(self) -> None:
        mod = _import_async_client()
        result = mod.MissionResult(completed=2, total=2, success=True)
        assert result.failed_waypoint is None


class TestBatteryState:
    def test_battery_state_fields(self) -> None:
        mod = _import_async_client()
        state = mod.BatteryState(voltage=12.6, percentage=0.85, state="ok")
        assert state.voltage == 12.6
        assert state.percentage == 0.85
        assert state.state == "ok"

    def test_battery_state_frozen(self) -> None:
        mod = _import_async_client()
        state = mod.BatteryState(voltage=11.0, percentage=0.15, state="low")
        with pytest.raises(FrozenInstanceError):
            state.voltage = 13.0  # type: ignore[misc]


class TestPayloadState:
    def test_payload_state_fields(self) -> None:
        mod = _import_async_client()
        state = mod.PayloadState(
            payload_id="p-001", name="gripper", connected=True, state=1
        )
        assert state.payload_id == "p-001"
        assert state.name == "gripper"
        assert state.connected is True
        assert state.state == 1

    def test_payload_state_frozen(self) -> None:
        mod = _import_async_client()
        state = mod.PayloadState(
            payload_id="p-002", name="arm", connected=False, state=0
        )
        with pytest.raises(FrozenInstanceError):
            state.connected = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Import failure test
# ---------------------------------------------------------------------------


class TestImportGuard:
    def test_client_requires_rclpy(self) -> None:
        """Importing async_client without rclpy raises ImportError."""
        # Remove cached module if present
        modules_to_remove = [k for k in sys.modules if "async_client" in k]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Override the autouse fixture's mocks with None for rclpy
        broken_mocks = {
            "rclpy": None,
            "rclpy.executors": None,
            "rclpy.node": None,
            "rclpy.qos": None,
            "rclpy.action": None,
        }
        with patch.dict(sys.modules, broken_mocks):
            with pytest.raises(ImportError, match="rclpy is required"):
                importlib.import_module("payload_interface.async_client")


# ---------------------------------------------------------------------------
# Mission execution tests
# ---------------------------------------------------------------------------


class TestMissionExecution:
    @pytest.fixture
    def mock_client(self) -> Any:
        """Create a client with mocked internals."""
        mod = _import_async_client()
        client = mod.AsyncPayloadClient(node_name="test_node")
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()
        return client

    @pytest.mark.asyncio
    async def test_mission_all_success(self, mock_client: Any) -> None:
        """All waypoints succeed -> MissionResult.success is True."""
        mod = _import_async_client()

        waypoints = [(1.0, 2.0, 0.0), (3.0, 4.0, 1.57), (5.0, 6.0, 3.14)]

        mock_client.send_nav_goal = AsyncMock(return_value=True)

        result = await mock_client.execute_mission(waypoints)

        assert result == mod.MissionResult(completed=3, total=3, success=True)
        assert mock_client.send_nav_goal.call_count == 3

    @pytest.mark.asyncio
    async def test_mission_partial_failure(self, mock_client: Any) -> None:
        """Second waypoint fails -> stops and reports failure."""
        mod = _import_async_client()

        waypoints = [(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (3.0, 0.0, 0.0)]

        mock_client.send_nav_goal = AsyncMock(side_effect=[True, False, True])

        result = await mock_client.execute_mission(waypoints)

        assert result == mod.MissionResult(
            completed=1, total=3, success=False, failed_waypoint=1
        )
        # Should not attempt third waypoint
        assert mock_client.send_nav_goal.call_count == 2


# ---------------------------------------------------------------------------
# E-stop service test
# ---------------------------------------------------------------------------


class TestEstop:
    @pytest.mark.asyncio
    async def test_estop_formats_request(self) -> None:
        """Verify trigger_estop builds the service request correctly."""
        mod = _import_async_client()

        client = mod.AsyncPayloadClient(node_name="estop_test")
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_response = MagicMock()
        mock_response.success = True

        client.call_service = AsyncMock(return_value=mock_response)

        # Patch EmergencyStop at module level
        mock_srv = MagicMock()
        mock_request_instance = MagicMock()
        mock_srv.Request.return_value = mock_request_instance

        with patch.object(mod, "EmergencyStop", mock_srv):
            result = await client.trigger_estop(reason="test halt")

        assert result is True
        client.call_service.assert_called_once()

        call_args = client.call_service.call_args
        assert call_args[0][0] == "/emergency_stop"
        assert call_args[0][1] is mock_srv
        assert call_args[0][2] is mock_request_instance
        assert mock_request_instance.reason == "test halt"


# ---------------------------------------------------------------------------
# Connect / Disconnect tests
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    @pytest.mark.asyncio
    async def test_connect_initializes_node(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient(node_name="conn_test")

        with patch.dict(sys.modules, _rclpy_mocks):
            rclpy_mod = sys.modules["rclpy"]
            rclpy_mod.ok.return_value = True
            mock_node = MagicMock()
            rclpy_mod.create_node.return_value = mock_node

            mock_executor_cls = sys.modules["rclpy.executors"].MultiThreadedExecutor
            mock_executor_instance = MagicMock()
            mock_executor_cls.return_value = mock_executor_instance

            await client.connect()

            assert client._connected is True
            assert client._node is mock_node
            rclpy_mod.create_node.assert_called_once_with("conn_test")
            mock_executor_instance.add_node.assert_called_once_with(mock_node)

    @pytest.mark.asyncio
    async def test_connect_idempotent(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True

        await client.connect()
        assert client._connected is True

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._executor = MagicMock()
        client._spin_thread = MagicMock()
        client._node = MagicMock()

        await client.disconnect()

        assert client._connected is False
        assert client._executor is None
        assert client._spin_thread is None
        assert client._node is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = False

        await client.disconnect()
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient(node_name="ctx_test")
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()

        async with client as c:
            assert c is client
            client.connect.assert_called_once()

        client.disconnect.assert_called_once()


# ---------------------------------------------------------------------------
# _ensure_connected tests
# ---------------------------------------------------------------------------


class TestEnsureConnected:
    def test_raises_when_not_connected(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = False

        with pytest.raises(RuntimeError, match="not connected"):
            client._ensure_connected()

    def test_raises_when_node_is_none(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = None

        with pytest.raises(RuntimeError, match="not connected"):
            client._ensure_connected()

    def test_passes_when_connected(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()

        client._ensure_connected()


# ---------------------------------------------------------------------------
# call_service tests
# ---------------------------------------------------------------------------


class TestCallService:
    @pytest.mark.asyncio
    async def test_service_not_available_raises(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_client = MagicMock()
        mock_client.wait_for_service.return_value = False
        client._node.create_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="not available"):
            await client.call_service(
                "/test_srv", MagicMock(), MagicMock(), timeout=1.0
            )

        client._node.destroy_client.assert_called_once_with(mock_client)

    @pytest.mark.asyncio
    async def test_service_success(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_srv_client = MagicMock()
        mock_srv_client.wait_for_service.return_value = True

        mock_future = MagicMock()
        expected_result = MagicMock()

        def fake_call_async(req):
            return mock_future

        mock_srv_client.call_async = fake_call_async
        client._node.create_client.return_value = mock_srv_client

        def trigger_callback(*args, **kwargs):
            cb = mock_future.add_done_callback.call_args[0][0]
            mock_future.exception.return_value = None
            mock_future.result.return_value = expected_result
            client._loop.call_soon_threadsafe(lambda: cb(mock_future))

        mock_future.add_done_callback = MagicMock(side_effect=trigger_callback)

        result = await asyncio.wait_for(
            client.call_service("/test", MagicMock(), MagicMock(), timeout=5.0),
            timeout=2.0,
        )
        assert result is expected_result


# ---------------------------------------------------------------------------
# subscribe_topic tests
# ---------------------------------------------------------------------------


class TestSubscribeTopic:
    @pytest.mark.asyncio
    async def test_subscribe_yields_messages(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_sub = MagicMock()
        captured_callback = None

        def create_sub(msg_type, topic, callback, qos):
            nonlocal captured_callback
            captured_callback = callback
            return mock_sub

        client._node.create_subscription = create_sub

        messages = []

        async def collect():
            count = 0
            async for msg in client.subscribe_topic("/test", MagicMock):
                messages.append(msg)
                count += 1
                if count >= 2:
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)

        captured_callback("msg1")
        captured_callback("msg2")
        await asyncio.sleep(0.05)

        client._connected = False
        await asyncio.wait_for(task, timeout=2.0)
        assert messages == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_subscribe_not_connected_raises(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = False
        client._node = None

        with pytest.raises(RuntimeError, match="not connected"):
            async for _ in client.subscribe_topic("/test", MagicMock):
                pass


# ---------------------------------------------------------------------------
# get_battery_state / get_payload_state tests
# ---------------------------------------------------------------------------


class TestGetBatteryState:
    @pytest.mark.asyncio
    async def test_battery_ok(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_msg = MagicMock()
        mock_msg.voltage = 12.6
        mock_msg.percentage = 0.85

        def create_sub(msg_type, topic, callback, qos):
            client._loop.call_soon(callback, mock_msg)
            return MagicMock()

        client._node.create_subscription = create_sub

        result = await client.get_battery_state()
        assert result.voltage == 12.6
        assert result.percentage == 0.85
        assert result.state == "ok"

    @pytest.mark.asyncio
    async def test_battery_low(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_msg = MagicMock()
        mock_msg.voltage = 11.0
        mock_msg.percentage = 0.15

        def create_sub(msg_type, topic, callback, qos):
            client._loop.call_soon(callback, mock_msg)
            return MagicMock()

        client._node.create_subscription = create_sub

        result = await client.get_battery_state()
        assert result.state == "low"

    @pytest.mark.asyncio
    async def test_battery_critical(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_msg = MagicMock()
        mock_msg.voltage = 9.5
        mock_msg.percentage = 0.05

        def create_sub(msg_type, topic, callback, qos):
            client._loop.call_soon(callback, mock_msg)
            return MagicMock()

        client._node.create_subscription = create_sub

        result = await client.get_battery_state()
        assert result.state == "critical"


class TestGetPayloadState:
    @pytest.mark.asyncio
    async def test_payload_state(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        mock_msg = MagicMock()
        mock_msg.payload_id = "p-100"
        mock_msg.name = "gripper"
        mock_msg.connected = True
        mock_msg.state = 2

        def create_sub(msg_type, topic, callback, qos):
            client._loop.call_soon(callback, mock_msg)
            return MagicMock()

        client._node.create_subscription = create_sub

        result = await client.get_payload_state()
        assert result.payload_id == "p-100"
        assert result.name == "gripper"
        assert result.connected is True
        assert result.state == 2


# ---------------------------------------------------------------------------
# send_nav_goal tests
# ---------------------------------------------------------------------------


class TestSendNavGoal:
    @pytest.mark.asyncio
    async def test_missing_nav2_raises(self) -> None:
        mod = _import_async_client()
        client = mod.AsyncPayloadClient()
        client._connected = True
        client._node = MagicMock()
        client._loop = asyncio.get_event_loop()

        with patch.object(mod, "NavigateToPose", None):
            with pytest.raises(ImportError, match="nav2_msgs"):
                await client.send_nav_goal(1.0, 2.0)
