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
