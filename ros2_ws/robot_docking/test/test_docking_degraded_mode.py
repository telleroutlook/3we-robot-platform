# SPDX-License-Identifier: Apache-2.0
"""Test DockingController graceful degradation when robot_interfaces is unavailable."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


class _FakeNode:
    """Minimal stand-in for rclpy.node.Node."""

    def __init__(self, name: str) -> None:
        self._param_values: dict = {}

    def declare_parameter(self, name: str, value=None):
        self._param_values[name] = value

    def get_parameter(self, name: str):
        mock_val = MagicMock()
        val = self._param_values.get(name, "")
        mock_val.get_parameter_value.return_value.string_value = (
            str(val) if isinstance(val, str) else ""
        )
        mock_val.get_parameter_value.return_value.double_value = (
            float(val) if isinstance(val, (int, float)) else 0.0
        )
        return mock_val

    def create_publisher(self, *args, **kwargs):
        return MagicMock()

    def create_subscription(self, *args, **kwargs):
        return MagicMock()

    def create_timer(self, *args, **kwargs):
        return MagicMock()

    def get_logger(self):
        return MagicMock()

    def get_clock(self):
        return MagicMock()


@pytest.fixture()
def _mock_rclpy():
    """Mock rclpy and its submodules so DockingController can be instantiated."""
    mock_rclpy = MagicMock()

    mock_node_module = types.ModuleType("rclpy.node")
    mock_node_module.Node = _FakeNode  # type: ignore[attr-defined]

    mock_action = MagicMock()
    mock_server_module = MagicMock()
    mock_server_module.ServerGoalHandle = MagicMock
    mock_cb_groups = MagicMock()
    mock_geometry = MagicMock()
    mock_std_msgs = MagicMock()

    mock_qos = MagicMock()
    modules = {
        "rclpy": mock_rclpy,
        "rclpy.node": mock_node_module,
        "rclpy.action": mock_action,
        "rclpy.action.server": mock_server_module,
        "rclpy.callback_groups": mock_cb_groups,
        "rclpy.qos": mock_qos,
        "geometry_msgs": mock_geometry,
        "geometry_msgs.msg": mock_geometry,
        "std_msgs": mock_std_msgs,
        "std_msgs.msg": mock_std_msgs,
    }

    with patch.dict(sys.modules, modules):
        yield modules


@pytest.fixture()
def _block_robot_interfaces(_mock_rclpy):
    """Block robot_interfaces from being imported."""
    with patch.dict(
        sys.modules, {"robot_interfaces": None, "robot_interfaces.action": None}
    ):
        yield


def _fresh_import():
    """Re-import DockingController to pick up mocked modules."""
    for key in list(sys.modules.keys()):
        if key.startswith("robot_docking"):
            del sys.modules[key]
    from robot_docking.docking_controller import DockingController

    return DockingController


class TestDockingDegradedMode:
    def test_controller_starts_without_action_interface(
        self, _block_robot_interfaces
    ) -> None:
        """DockingController must initialize cleanly when robot_interfaces is missing."""
        DockingController = _fresh_import()
        controller = DockingController()
        assert controller._action_server is None

    def test_make_result_returns_none_without_interfaces(
        self, _block_robot_interfaces
    ) -> None:
        """_make_result gracefully returns None when robot_interfaces is missing."""
        DockingController = _fresh_import()
        controller = DockingController()
        result = controller._make_result(True, "", 0.0)
        assert result is None

    def test_publish_feedback_does_not_raise_without_interfaces(
        self, _block_robot_interfaces
    ) -> None:
        """_publish_feedback silently no-ops when robot_interfaces is missing."""
        DockingController = _fresh_import()
        controller = DockingController()
        mock_goal_handle = MagicMock()
        controller._publish_feedback(mock_goal_handle)
