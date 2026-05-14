# SPDX-License-Identifier: Apache-2.0
"""Tests for backend implementations."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from threewe.backends import BackendBase
from threewe.backends.gazebo import GazeboBackend
from threewe.backends.real import RealBackend
from threewe.config import RobotConfig
from threewe.types import (
    BatteryState,
    ExploreResult,
    IMUData,
    LaserScan,
    MoveResult,
    OccupancyGrid,
    Pose2D,
    RGBDImage,
    Velocity,
)


class TestBackendBase:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            BackendBase()  # type: ignore[abstract]

    def test_gazebo_is_subclass(self):
        assert issubclass(GazeboBackend, BackendBase)

    def test_real_is_subclass(self):
        assert issubclass(RealBackend, BackendBase)


class TestGazeboBackendOffline:
    """Tests that run without ROS2 (no connect())."""

    def setup_method(self):
        self.config = RobotConfig()
        self.backend = GazeboBackend(self.config, scene="test_scene")

    def test_not_connected_initially(self):
        assert self.backend.is_connected is False

    def test_get_camera_image_returns_zeros(self):
        img = self.backend.get_camera_image()
        assert img.shape == (480, 640, 3)
        assert img.dtype == np.uint8
        assert np.all(img == 0)

    def test_get_rgbd_image_returns_valid_struct(self):
        rgbd = self.backend.get_rgbd_image()
        assert isinstance(rgbd, RGBDImage)
        assert rgbd.rgb.shape == (480, 640, 3)
        assert rgbd.depth.shape == (480, 640)
        assert rgbd.depth.dtype == np.float32

    def test_get_lidar_scan_returns_valid_struct(self):
        scan = self.backend.get_lidar_scan()
        assert isinstance(scan, LaserScan)
        assert scan.ranges.shape == (360,)
        assert scan.angles.shape == (360,)
        assert scan.range_max == 12.0

    def test_get_pose_returns_origin(self):
        pose = self.backend.get_pose()
        assert isinstance(pose, Pose2D)
        assert pose.x == 0.0
        assert pose.y == 0.0
        assert pose.theta == 0.0

    def test_get_velocity_returns_zero(self):
        vel = self.backend.get_velocity()
        assert isinstance(vel, Velocity)
        assert vel.vx == 0.0
        assert vel.vy == 0.0
        assert vel.omega == 0.0

    def test_get_imu_returns_valid_struct(self):
        imu = self.backend.get_imu()
        assert isinstance(imu, IMUData)
        assert imu.acceleration.shape == (3,)
        assert imu.angular_velocity.shape == (3,)
        assert imu.orientation.shape == (4,)

    def test_get_battery_state_returns_full(self):
        bat = self.backend.get_battery_state()
        assert isinstance(bat, BatteryState)
        assert bat.voltage == 7.4
        assert bat.percentage == 1.0

    def test_get_map_returns_unknown(self):
        grid = self.backend.get_map()
        assert isinstance(grid, OccupancyGrid)
        assert grid.data.shape == (100, 100)
        assert np.all(grid.data == -1)

    def test_set_velocity_does_not_raise(self):
        self.backend.set_velocity(0.1, 0.0, 0.5)

    def test_stop_does_not_raise(self):
        self.backend.stop()

    @pytest.mark.asyncio
    async def test_move_to_returns_success(self):
        result = await self.backend.move_to(2.0, 3.0, 1.57)
        assert isinstance(result, MoveResult)
        assert result.success is True
        assert result.final_pose.x == 2.0
        assert result.final_pose.y == 3.0

    @pytest.mark.asyncio
    async def test_move_forward_returns_success(self):
        result = await self.backend.move_forward(1.0)
        assert isinstance(result, MoveResult)
        assert result.success is True
        assert result.distance == 1.0

    @pytest.mark.asyncio
    async def test_rotate_returns_success(self):
        result = await self.backend.rotate(1.57)
        assert isinstance(result, MoveResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_explore_returns_result(self):
        result = await self.backend.explore(timeout=1.0)
        assert isinstance(result, ExploreResult)
        assert result.coverage == 0.0

    def test_disconnect_when_not_connected(self):
        self.backend.disconnect()
        assert self.backend.is_connected is False


class TestRealBackendOffline:
    """Tests that run without ROS2 (no connect())."""

    def setup_method(self):
        self.config = RobotConfig()
        self.backend = RealBackend(self.config)

    def test_not_connected_initially(self):
        assert self.backend.is_connected is False

    def test_get_camera_image_returns_zeros(self):
        img = self.backend.get_camera_image()
        assert img.shape == (480, 640, 3)
        assert img.dtype == np.uint8

    def test_get_pose_returns_origin(self):
        pose = self.backend.get_pose()
        assert pose.x == 0.0
        assert pose.y == 0.0

    @pytest.mark.asyncio
    async def test_move_to_returns_success(self):
        result = await self.backend.move_to(1.0, 1.0)
        assert result.success is True

    def test_disconnect_when_not_connected(self):
        self.backend.disconnect()
        assert self.backend.is_connected is False


class TestGazeboBackendConnect:
    """Test connection behavior with mocked rclpy."""

    def test_connect_raises_without_rclpy(self):
        config = RobotConfig()
        backend = GazeboBackend(config)
        with patch.dict("sys.modules", {"rclpy": None}):
            with pytest.raises(ImportError, match="rclpy"):
                backend.connect()

    def test_connect_success_with_mocked_rclpy(self):
        config = RobotConfig()
        backend = GazeboBackend(config)

        mock_rclpy = MagicMock()
        mock_rclpy.ok.return_value = True

        mock_node = MagicMock()
        mock_rclpy.create_node.return_value = mock_node

        with patch.dict(
            "sys.modules",
            {
                "rclpy": mock_rclpy,
                "rclpy.qos": MagicMock(),
                "rclpy.action": MagicMock(),
                "sensor_msgs": MagicMock(),
                "sensor_msgs.msg": MagicMock(),
                "geometry_msgs": MagicMock(),
                "geometry_msgs.msg": MagicMock(),
                "nav_msgs": MagicMock(),
                "nav_msgs.msg": MagicMock(),
                "nav2_msgs": MagicMock(),
                "nav2_msgs.action": MagicMock(),
            },
        ):
            backend.connect()
            assert backend.is_connected is True
            backend.disconnect()
            assert backend.is_connected is False


class TestRealBackendConnect:
    """Test connection behavior with mocked rclpy."""

    def test_connect_raises_without_rclpy(self):
        config = RobotConfig()
        backend = RealBackend(config)
        with patch.dict("sys.modules", {"rclpy": None}):
            with pytest.raises(ImportError, match="rclpy"):
                backend.connect()


class TestSim2RealConsistencyContract:
    """Verify that both backends return data in identical formats."""

    def setup_method(self):
        self.config = RobotConfig()
        self.gazebo = GazeboBackend(self.config)
        self.real = RealBackend(self.config)

    def test_camera_image_same_shape_and_dtype(self):
        gz_img = self.gazebo.get_camera_image()
        real_img = self.real.get_camera_image()
        assert gz_img.shape == real_img.shape
        assert gz_img.dtype == real_img.dtype

    def test_lidar_scan_same_format(self):
        gz_scan = self.gazebo.get_lidar_scan()
        real_scan = self.real.get_lidar_scan()
        assert gz_scan.ranges.shape == real_scan.ranges.shape
        assert gz_scan.ranges.dtype == real_scan.ranges.dtype
        assert gz_scan.range_max == real_scan.range_max

    def test_pose_same_type(self):
        gz_pose = self.gazebo.get_pose()
        real_pose = self.real.get_pose()
        assert type(gz_pose) is type(real_pose)

    def test_velocity_same_type(self):
        gz_vel = self.gazebo.get_velocity()
        real_vel = self.real.get_velocity()
        assert type(gz_vel) is type(real_vel)

    def test_imu_same_shape(self):
        gz_imu = self.gazebo.get_imu()
        real_imu = self.real.get_imu()
        assert gz_imu.acceleration.shape == real_imu.acceleration.shape
        assert gz_imu.orientation.shape == real_imu.orientation.shape

    def test_map_same_dtype(self):
        gz_map = self.gazebo.get_map()
        real_map = self.real.get_map()
        assert gz_map.data.dtype == real_map.data.dtype


class TestCameraChannelOrder:
    """Verify BGR→RGB conversion in _image_callback."""

    def _make_image_msg(self, data: bytes, encoding: str, h: int, w: int):
        msg = MagicMock()
        msg.height = h
        msg.width = w
        msg.encoding = encoding
        msg.data = data
        return msg

    def test_bgr8_converted_to_rgb(self):
        from threewe.backends._ros2_node import ROS2Node

        node = object.__new__(ROS2Node)
        node._state_lock = __import__("threading").Lock()
        node._latest_image = None

        h, w = 2, 2
        bgr_array = np.zeros((h, w, 3), dtype=np.uint8)
        bgr_array[0, 0] = [255, 0, 0]  # pure blue in BGR
        bgr_array[1, 1] = [0, 255, 0]  # pure green in BGR

        msg = self._make_image_msg(bgr_array.tobytes(), "bgr8", h, w)
        node._image_callback(msg)

        result = node._latest_image
        assert result[0, 0, 0] == 0  # R channel (was B=255 in BGR)
        assert result[0, 0, 2] == 255  # B channel (was B=255, now at index 2)
        assert result[1, 1, 1] == 255  # G stays at index 1

    def test_rgb8_unchanged(self):
        from threewe.backends._ros2_node import ROS2Node

        node = object.__new__(ROS2Node)
        node._state_lock = __import__("threading").Lock()
        node._latest_image = None

        h, w = 2, 2
        rgb_array = np.zeros((h, w, 3), dtype=np.uint8)
        rgb_array[0, 0] = [255, 0, 0]  # pure red in RGB

        msg = self._make_image_msg(rgb_array.tobytes(), "rgb8", h, w)
        node._image_callback(msg)

        result = node._latest_image
        assert result[0, 0, 0] == 255  # R channel unchanged
        assert result[0, 0, 1] == 0
        assert result[0, 0, 2] == 0
